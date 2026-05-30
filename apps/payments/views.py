from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db.models import Sum, Q, Count
from decimal import Decimal

from .models import PaymentLedger
from apps.students.models import Student
from apps.classes.models import SchoolClass
from apps.users.permissions import finance_required, it_admin_required, staff_view_required, role_required
from apps.audit.utils import log_action
from apps.notifications.utils import notify_user, notify_role


@login_required
def payment_dashboard(request):
    user = request.user
    context = {}

    if user.is_finance:
        context['pending_finance'] = PaymentLedger.objects.filter(
            status='PENDING_FINANCE'
        ).order_by('-created_at')[:50]
        context['pending_it'] = PaymentLedger.objects.filter(
            status='PENDING_IT', finance_user=user
        ).order_by('-created_at')[:50]

    elif user.is_it_admin:
        context['pending_approval'] = PaymentLedger.objects.filter(
            status='PENDING_IT'
        ).select_related('student', 'finance_user', 'hm_approval_user').order_by('-created_at')

    if user.can_view_all or user.is_finance or user.is_hr:
        context['total_collected'] = PaymentLedger.objects.filter(
            status='APPROVED'
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')

        context['students_owing'] = Student.objects.filter(
            is_active=True, outstanding_balance__gt=0
        ).count()

        # Class-by-class collection performance
        context['by_class'] = SchoolClass.objects.filter(is_active=True).annotate(
            students=Count('students', filter=Q(students__is_active=True)),
            owing=Count('students', filter=Q(students__is_active=True, students__outstanding_balance__gt=0)),
        )

    return render(request, 'payments/dashboard.html', context)


@finance_required
def finance_submit_payment(request):
    """Step 1: Finance temporarily approves and submits to IT Admin.
    For CASH/CHEQUE, also requires HM/Asst HM image upload at submit time."""
    if request.method == 'POST':
        try:
            student = get_object_or_404(Student, id=request.POST['student_id'])

            with transaction.atomic():
                payment = PaymentLedger(
                    student=student,
                    amount_paid=request.POST['amount_paid'],
                    payment_method=request.POST['payment_method'],
                    transaction_id=request.POST.get('transaction_id', ''),
                    payment_date=request.POST['payment_date'],
                    academic_year=request.POST['academic_year'],
                    semester=request.POST.get('semester', ''),
                    finance_user=request.user,
                    finance_notes=request.POST.get('finance_notes', ''),
                    status='PENDING_IT',
                )

                # File uploads
                if 'receipt_image' in request.FILES:
                    payment.receipt_image = request.FILES['receipt_image']
                if 'cheque_image' in request.FILES:
                    payment.cheque_image = request.FILES['cheque_image']
                if 'hm_signature_image' in request.FILES:
                    payment.hm_signature_image = request.FILES['hm_signature_image']

                payment.save()

                # Generate auto-named note file
                note_content = payment.generate_note_content()
                payment.note_file.save(payment.note_filename, ContentFile(note_content.encode('utf-8')))
                payment.save()

            log_action(request.user, 'SUBMIT_PAYMENT', 'payment_ledger', payment.id, request,
                       new_values={
                           'student': student.full_name,
                           'amount': str(payment.amount_paid),
                           'method': payment.payment_method,
                       })

            # Notify IT Admin
            notify_role('IT_ADMIN', 'Payment pending approval',
                        f"Finance submitted a {payment.payment_method} payment of {payment.amount_paid} "
                        f"for {student.full_name}. Approve in payments dashboard.",
                        link=f'/payments/{payment.id}/')

            messages.success(request, "Payment submitted to IT Admin for approval.")
            return redirect('payment_dashboard')

        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'payments/finance_submit.html', {
        'students': Student.objects.filter(is_active=True).order_by('full_name'),
        'academic_year': timezone.now().year,
    })


@finance_required
def edit_pending_payment(request, payment_id):
    """Finance can edit ONLY while in PENDING_FINANCE or PENDING_IT status,
    and only their own submissions, before IT approves."""
    payment = get_object_or_404(PaymentLedger, id=payment_id)

    if payment.is_immutable:
        messages.error(request, "Approved payments cannot be edited. Submit a reversal instead.")
        return redirect('payment_detail', payment_id=payment.id)

    if payment.finance_user != request.user:
        messages.error(request, "You can only edit payments you submitted.")
        return redirect('payment_dashboard')

    if request.method == 'POST':
        old = {'amount': str(payment.amount_paid), 'method': payment.payment_method}
        payment.amount_paid = request.POST['amount_paid']
        payment.payment_method = request.POST['payment_method']
        payment.transaction_id = request.POST.get('transaction_id', '')
        payment.finance_notes = request.POST.get('finance_notes', '')
        payment.save()
        new = {'amount': str(payment.amount_paid), 'method': payment.payment_method}
        log_action(request.user, 'EDIT_PAYMENT', 'payment_ledger', payment.id, request,
                   old_values=old, new_values=new)
        messages.success(request, "Payment updated.")
        return redirect('payment_detail', payment_id=payment.id)

    return render(request, 'payments/edit.html', {'payment': payment})


@it_admin_required
def it_admin_approve(request, payment_id):
    """Step 2: IT Admin permanently approves. After this, immutable."""
    payment = get_object_or_404(PaymentLedger, id=payment_id)

    if payment.status != 'PENDING_IT':
        messages.error(request, "This payment is not in the pending state.")
        return redirect('payment_dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        with transaction.atomic():
            if action == 'approve':
                payment.it_admin_user = request.user
                payment.it_admin_approved_at = timezone.now()
                payment.it_admin_notes = request.POST.get('notes', '')
                payment.status = 'APPROVED'
                payment.save()

                # Recalculate student balance
                payment.student.recalculate_balance()

                log_action(request.user, 'APPROVE_PAYMENT', 'payment_ledger', payment.id, request,
                           new_values={'status': 'APPROVED', 'amount': str(payment.amount_paid)})

                # Notify finance + headmaster
                notify_user(payment.finance_user, 'Payment approved',
                            f"Payment of {payment.amount_paid} for {payment.student.full_name} approved.")
                notify_role('HEADMASTER', 'Payment approved',
                            f"Payment of {payment.amount_paid} for {payment.student.full_name} finalized.")

                messages.success(request, "Payment approved and reflected in student balance.")
            elif action == 'reject':
                payment.status = 'REJECTED'
                payment.rejection_reason = request.POST.get('reason', '')
                payment.it_admin_user = request.user
                payment.it_admin_approved_at = timezone.now()
                payment.save()
                log_action(request.user, 'REJECT_PAYMENT', 'payment_ledger', payment.id, request,
                           new_values={'reason': payment.rejection_reason})
                notify_user(payment.finance_user, 'Payment rejected',
                            f"Payment for {payment.student.full_name} rejected: {payment.rejection_reason}")
                messages.success(request, "Payment rejected.")

        return redirect('payment_dashboard')

    return render(request, 'payments/it_admin_approve.html', {'payment': payment})


@it_admin_required
def reverse_payment(request, payment_id):
    """Create a reversal entry for an approved payment (immutable original)."""
    original = get_object_or_404(PaymentLedger, id=payment_id)

    if original.status != 'APPROVED':
        messages.error(request, "Only approved payments can be reversed.")
        return redirect('payment_detail', payment_id=original.id)

    if request.method == 'POST':
        with transaction.atomic():
            reversal = PaymentLedger.objects.create(
                student=original.student,
                amount_paid=-original.amount_paid,  # negative
                payment_method=original.payment_method,
                transaction_id=f"REVERSAL-{original.id}",
                payment_date=timezone.now(),
                academic_year=original.academic_year,
                semester=original.semester,
                finance_user=original.finance_user,
                it_admin_user=request.user,
                it_admin_approved_at=timezone.now(),
                status='APPROVED',
                reversal_of=original,
                reversal_reason=request.POST['reason'],
            )

            original.status = 'REVERSED'
            original.save()

            original.student.recalculate_balance()

        log_action(request.user, 'REVERSE_PAYMENT', 'payment_ledger', reversal.id, request,
                   new_values={'original_id': original.id, 'reason': reversal.reversal_reason})
        messages.success(request, "Payment reversed.")
        return redirect('payment_detail', payment_id=original.id)

    return render(request, 'payments/reverse.html', {'payment': original})


@login_required
def payment_detail(request, payment_id):
    payment = get_object_or_404(PaymentLedger, id=payment_id)
    # Audit view
    log_action(request.user, 'VIEW_PAYMENT', 'payment_ledger', payment.id, request)
    return render(request, 'payments/detail.html', {'payment': payment})


@staff_view_required
def outstanding_balances(request):
    """List of students with outstanding balances."""
    students = Student.objects.filter(is_active=True, outstanding_balance__gt=0).select_related('current_class')

    class_id = request.GET.get('class')
    if class_id:
        students = students.filter(current_class_id=class_id)

    total_outstanding = students.aggregate(total=Sum('outstanding_balance'))['total'] or Decimal('0')

    return render(request, 'payments/outstanding.html', {
        'students': students,
        'total_outstanding': total_outstanding,
        'classes': SchoolClass.objects.filter(is_active=True),
    })


@staff_view_required
def class_performance(request):
    """School fees collection performance by class."""
    classes = SchoolClass.objects.filter(is_active=True).annotate(
        total_students=Count('students', filter=Q(students__is_active=True)),
        owing_students=Count('students', filter=Q(students__is_active=True, students__outstanding_balance__gt=0)),
        total_due=Sum('students__total_fees_due', filter=Q(students__is_active=True)),
        total_paid=Sum('students__total_fees_paid', filter=Q(students__is_active=True)),
    )

    return render(request, 'payments/class_performance.html', {'classes': classes})
