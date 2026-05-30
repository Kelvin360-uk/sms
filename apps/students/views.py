from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
import csv

from .models import Student
from apps.classes.models import SchoolClass
from apps.users.permissions import it_admin_required, staff_view_required, can_view_all_required
from apps.users.models import DownloadPermission
from apps.audit.utils import log_action
from django.utils import timezone


@login_required
def student_list(request):
    """List students with role-based filtering."""
    user = request.user
    qs = Student.objects.filter(is_active=True).select_related('current_class')

    # Class teachers see only their class
    if user.is_class_teacher and hasattr(user, 'teacher_profile') and user.teacher_profile.assigned_class:
        qs = qs.filter(current_class=user.teacher_profile.assigned_class)
    elif user.is_teacher and not user.is_class_teacher:
        # Regular teacher: see students from classes they teach
        if hasattr(user, 'teacher_profile'):
            qs = qs.filter(current_class__in=user.teacher_profile.classes_taught.all())

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(student_id__icontains=q))

    # Filter by class
    class_id = request.GET.get('class')
    if class_id:
        qs = qs.filter(current_class_id=class_id)

    # Filter by gender
    gender = request.GET.get('gender')
    if gender in ('M', 'F'):
        qs = qs.filter(gender=gender)

    context = {
        'students': qs[:500],  # limit for performance; pagination would be next step
        'classes': SchoolClass.objects.filter(is_active=True),
        'total_boys': qs.filter(gender='M').count(),
        'total_girls': qs.filter(gender='F').count(),
        'total': qs.count(),
        'q': q,
    }
    return render(request, 'students/list.html', context)


@it_admin_required
def create_student(request):
    if request.method == 'POST':
        try:
            student = Student.objects.create(
                student_id=request.POST['student_id'],
                full_name=request.POST['full_name'],
                date_of_birth=request.POST['date_of_birth'],
                gender=request.POST['gender'],
                residence=request.POST['residence'],
                parent_guardian_name=request.POST['parent_guardian_name'],
                parent_guardian_phone=request.POST['parent_guardian_phone'],
                parent_guardian_email=request.POST.get('parent_guardian_email', ''),
                parent_guardian_relation=request.POST.get('parent_guardian_relation', 'Guardian'),
                current_class_id=request.POST.get('current_class') or None,
                total_fees_due=request.POST.get('total_fees_due', 0),
            )
            student.outstanding_balance = student.total_fees_due
            student.save()
            log_action(request.user, 'CREATE_STUDENT', 'students', student.id, request,
                       new_values={'student_id': student.student_id, 'full_name': student.full_name})
            messages.success(request, f"Student {student.full_name} enrolled.")
            return redirect('student_list')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'students/create.html', {
        'classes': SchoolClass.objects.filter(is_active=True)
    })


@login_required
def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    user = request.user

    # Access control: teachers can only view their own class students
    if user.is_class_teacher and hasattr(user, 'teacher_profile'):
        if student.current_class != user.teacher_profile.assigned_class:
            messages.error(request, "You can only view students in your class.")
            return redirect('student_list')
    elif user.is_teacher and not user.is_class_teacher:
        if hasattr(user, 'teacher_profile'):
            if student.current_class not in user.teacher_profile.classes_taught.all():
                messages.error(request, "You don't teach this student's class.")
                return redirect('student_list')

    from apps.exams.models import ExamResult
    from apps.payments.models import PaymentLedger

    context = {
        'student': student,
        'exam_results': ExamResult.objects.filter(student=student).order_by('-created_at')[:20],
        'payments': PaymentLedger.objects.filter(student=student, status='APPROVED').order_by('-created_at'),
        'pending_payments': PaymentLedger.objects.filter(
            student=student, status__in=['PENDING_FINANCE', 'PENDING_IT']
        ).order_by('-created_at'),
    }
    return render(request, 'students/detail.html', context)


@it_admin_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    old_values = {f: str(getattr(student, f)) for f in
                  ['full_name', 'residence', 'parent_guardian_phone', 'total_fees_due']}

    if request.method == 'POST':
        student.full_name = request.POST['full_name']
        student.residence = request.POST['residence']
        student.parent_guardian_name = request.POST['parent_guardian_name']
        student.parent_guardian_phone = request.POST['parent_guardian_phone']
        student.parent_guardian_email = request.POST.get('parent_guardian_email', '')
        student.total_fees_due = request.POST.get('total_fees_due', student.total_fees_due)
        if request.POST.get('current_class'):
            student.current_class_id = request.POST['current_class']
        student.save()
        student.recalculate_balance()

        new_values = {f: str(getattr(student, f)) for f in
                      ['full_name', 'residence', 'parent_guardian_phone', 'total_fees_due']}
        log_action(request.user, 'EDIT_STUDENT', 'students', student.id, request,
                   old_values=old_values, new_values=new_values)
        messages.success(request, "Student updated.")
        return redirect('student_detail', student_id=student.id)

    return render(request, 'students/edit.html', {
        'student': student,
        'classes': SchoolClass.objects.filter(is_active=True),
    })


@it_admin_required
def export_students(request):
    """IT Admin only - CSV download."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="students_{timezone.now().date()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Full Name', 'DOB', 'Gender', 'Class', 'Parent Phone',
                     'Total Fees Due', 'Total Paid', 'Outstanding'])
    for s in Student.objects.filter(is_active=True).select_related('current_class'):
        writer.writerow([s.student_id, s.full_name, s.date_of_birth, s.gender,
                         s.current_class.name if s.current_class else '', s.parent_guardian_phone,
                         s.total_fees_due, s.total_fees_paid, s.outstanding_balance])
    log_action(request.user, 'EXPORT_STUDENTS', 'students', 0, request)
    return response


@staff_view_required
def student_statistics(request):
    """Overall statistics view: gender split, class breakdowns."""
    total_students = Student.objects.filter(is_active=True).count()
    boys = Student.objects.filter(is_active=True, gender='M').count()
    girls = Student.objects.filter(is_active=True, gender='F').count()

    by_class = SchoolClass.objects.filter(is_active=True).annotate(
        boys=Count('students', filter=Q(students__is_active=True, students__gender='M')),
        girls=Count('students', filter=Q(students__is_active=True, students__gender='F')),
        total=Count('students', filter=Q(students__is_active=True)),
    )

    return render(request, 'students/statistics.html', {
        'total_students': total_students, 'boys': boys, 'girls': girls,
        'by_class': by_class,
    })
