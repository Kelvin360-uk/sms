from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count
from django.db import transaction
from django.http import HttpResponse
import csv

from .models import ExamResult, ExamSession, ExamReminder
from apps.students.models import Student
from apps.classes.models import SchoolClass, Subject
from apps.teachers.models import Teacher
from apps.users.permissions import role_required, teacher_required, it_admin_required, role_required
from apps.users.models import DownloadPermission
from apps.audit.utils import log_action
from apps.notifications.utils import notify_exam_uploaded


@login_required
def exam_dashboard(request):
    user = request.user
    context = {'sessions': ExamSession.objects.filter(is_active=True)}

    if user.is_teacher or user.is_class_teacher:
        try:
            teacher = user.teacher_profile
            context['my_results'] = ExamResult.objects.filter(teacher=teacher).order_by('-created_at')[:20]
            context['pending_review'] = ExamResult.objects.filter(
                teacher=teacher, status='DRAFT'
            ).count()
            if user.is_class_teacher and teacher.assigned_class:
                context['my_class_pending'] = ExamResult.objects.filter(
                    student__current_class=teacher.assigned_class,
                    status='SUBMITTED'
                )
        except Teacher.DoesNotExist:
            pass

    elif user.is_asst_headmaster:
        context['pending_finalization'] = ExamResult.objects.filter(
            status='CLASS_TEACHER_REVIEWED'
        ).order_by('-updated_at')[:50]

    elif user.can_view_all:
        context['recent_results'] = ExamResult.objects.order_by('-created_at')[:30]

    return render(request, 'exams/dashboard.html', context)


@teacher_required
def submit_result(request):
    """Teacher submits exam result for one student."""
    if request.method == 'POST':
        try:
            teacher = request.user.teacher_profile
            student = get_object_or_404(Student, id=request.POST['student_id'])
            subject = get_object_or_404(Subject, id=request.POST['subject_id'])
            session = get_object_or_404(ExamSession, id=request.POST['exam_session_id'])

            with transaction.atomic():
                result, created = ExamResult.objects.get_or_create(
                    student=student, subject=subject, exam_session=session,
                    defaults={
                        'teacher': teacher,
                        'score': request.POST['score'],
                        'max_score': request.POST.get('max_score', 100),
                        'teacher_remarks': request.POST.get('teacher_remarks', ''),
                        'status': 'SUBMITTED',
                    }
                )
                if not created:
                    # Update existing draft
                    if result.status not in ('DRAFT', 'SUBMITTED'):
                        messages.error(request, "This result has progressed past submission.")
                        return redirect('exam_dashboard')
                    result.score = request.POST['score']
                    result.max_score = request.POST.get('max_score', 100)
                    result.teacher_remarks = request.POST.get('teacher_remarks', '')
                    result.status = 'SUBMITTED'
                    result.version += 1

                result.calculate_grade()
                result.save()

            log_action(request.user, 'SUBMIT_EXAM_RESULT', 'exam_results', result.id, request,
                       new_values={'student': student.full_name, 'subject': subject.code, 'score': str(result.score)})

            # Notify IT Admin and Headmaster
            notify_exam_uploaded(result, request.user)

            messages.success(request, "Exam result submitted.")
            return redirect('exam_dashboard')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    teacher = getattr(request.user, 'teacher_profile', None)
    if not teacher:
        messages.error(request, "No teacher profile linked.")
        return redirect('dashboard')

    # Students: classes this teacher teaches
    if request.user.is_class_teacher and teacher.assigned_class:
        students = Student.objects.filter(current_class=teacher.assigned_class, is_active=True)
    else:
        students = Student.objects.filter(current_class__in=teacher.classes_taught.all(), is_active=True)

    return render(request, 'exams/submit.html', {
        'students': students,
        'subjects': teacher.subjects_taught.all(),
        'sessions': ExamSession.objects.filter(is_active=True),
    })


@role_required('CLASS_TEACHER')
def class_teacher_review(request, result_id):
    """Class teacher adds remarks before sending to Asst Headmaster."""
    result = get_object_or_404(ExamResult, id=result_id)
    teacher = request.user.teacher_profile

    # Verify this is their class
    if result.student.current_class != teacher.assigned_class:
        messages.error(request, "You can only review results from your assigned class.")
        return redirect('exam_dashboard')

    if request.method == 'POST':
        with transaction.atomic():
            result.class_teacher_remarks = request.POST.get('remarks', '')
            result.class_teacher_signature = request.user
            result.class_teacher_signed_at = timezone.now()
            result.status = 'CLASS_TEACHER_REVIEWED'
            result.version += 1
            result.save()

        log_action(request.user, 'CLASS_TEACHER_REVIEW', 'exam_results', result.id, request,
                   new_values={'remarks': result.class_teacher_remarks})
        messages.success(request, "Result reviewed and forwarded to Assistant Headmaster.")
        return redirect('class_teacher_pending')

    return render(request, 'exams/class_teacher_review.html', {'result': result})


@role_required('CLASS_TEACHER')
def class_teacher_pending(request):
    """List results in my class pending my review."""
    teacher = request.user.teacher_profile
    if not teacher.assigned_class:
        messages.info(request, "You are not assigned to any class.")
        return redirect('exam_dashboard')

    pending = ExamResult.objects.filter(
        student__current_class=teacher.assigned_class,
        status='SUBMITTED'
    ).select_related('student', 'subject', 'teacher').order_by('-created_at')

    return render(request, 'exams/class_teacher_pending.html', {'pending': pending})


@role_required('ASST_HEADMASTER')
def asst_hm_finalize(request, result_id):
    """Asst Headmaster gives final remarks and signature."""
    result = get_object_or_404(ExamResult, id=result_id)

    if result.status != 'CLASS_TEACHER_REVIEWED':
        messages.error(request, "This result is not ready for finalization.")
        return redirect('asst_hm_pending')

    if request.method == 'POST':
        with transaction.atomic():
            result.asst_headmaster_remarks = request.POST.get('remarks', '')
            result.asst_headmaster_signature = request.user
            result.asst_headmaster_signed_at = timezone.now()
            result.status = 'FINAL'
            result.version += 1
            result.save()

        log_action(request.user, 'FINALIZE_EXAM_RESULT', 'exam_results', result.id, request,
                   new_values={'remarks': result.asst_headmaster_remarks})
        messages.success(request, "Result finalized.")
        return redirect('asst_hm_pending')

    return render(request, 'exams/asst_hm_review.html', {'result': result})


@role_required('ASST_HEADMASTER')
def asst_hm_pending(request):
    pending = ExamResult.objects.filter(
        status='CLASS_TEACHER_REVIEWED'
    ).select_related('student', 'subject', 'teacher').order_by('-updated_at')
    return render(request, 'exams/asst_hm_pending.html', {'pending': pending})


@role_required('ASST_HEADMASTER', 'HEADMASTER', 'IT_ADMIN')
def create_reminder(request):
    if request.method == 'POST':
        reminder = ExamReminder.objects.create(
            exam_session_id=request.POST['exam_session_id'],
            title=request.POST['title'],
            message=request.POST['message'],
            deadline=request.POST['deadline'],
            created_by=request.user,
            target_role=request.POST.get('target_role', 'TEACHER'),
        )
        log_action(request.user, 'CREATE_REMINDER', 'exam_reminders', reminder.id, request)

        # Notify all teachers
        from apps.notifications.utils import notify_role
        notify_role(reminder.target_role, f"Reminder: {reminder.title}",
                    f"{reminder.message} (Deadline: {reminder.deadline})", link='/exams/')

        messages.success(request, "Reminder sent.")
        return redirect('exam_dashboard')

    return render(request, 'exams/create_reminder.html', {
        'sessions': ExamSession.objects.filter(is_active=True),
    })


@it_admin_required
def create_session(request):
    if request.method == 'POST':
        session = ExamSession.objects.create(
            name=request.POST['name'],
            academic_year=request.POST['academic_year'],
            start_date=request.POST['start_date'],
            end_date=request.POST['end_date'],
            submission_deadline=request.POST['submission_deadline'],
        )
        log_action(request.user, 'CREATE_EXAM_SESSION', 'exam_sessions', session.id, request)
        messages.success(request, f"Exam session {session.name} created.")
        return redirect('exam_dashboard')
    return render(request, 'exams/create_session.html')


@login_required
def view_results(request, student_id):
    """View finalized results for a student."""
    student = get_object_or_404(Student, id=student_id)
    user = request.user

    # Access check
    if user.is_class_teacher and hasattr(user, 'teacher_profile'):
        if student.current_class != user.teacher_profile.assigned_class:
            messages.error(request, "Not your class.")
            return redirect('exam_dashboard')
    elif user.is_teacher and not user.is_class_teacher:
        if hasattr(user, 'teacher_profile'):
            if student.current_class not in user.teacher_profile.classes_taught.all():
                messages.error(request, "Not your class.")
                return redirect('exam_dashboard')

    results = ExamResult.objects.filter(student=student).select_related('subject', 'exam_session', 'teacher')
    return render(request, 'exams/student_results.html', {'student': student, 'results': results})


@login_required
def download_results(request, student_id):
    """Download requires explicit permission for teachers; IT Admin always allowed."""
    user = request.user
    student = get_object_or_404(Student, id=student_id)

    if not user.is_it_admin:
        # Check for granted permission
        has_perm = DownloadPermission.objects.filter(
            user=user, resource_type='exam_results', revoked=False,
            expires_at__gt=timezone.now()
        ).exists()
        if not has_perm:
            messages.error(request, "Download requires IT Admin permission.")
            return redirect('view_results', student_id=student_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="results_{student.student_id}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Subject', 'Session', 'Score', 'Max', 'Grade', 'Teacher Remarks',
                     'Class Teacher Remarks', 'Asst HM Remarks', 'Status'])
    for r in ExamResult.objects.filter(student=student).select_related('subject', 'exam_session'):
        writer.writerow([r.subject.code, r.exam_session.name, r.score, r.max_score, r.grade,
                         r.teacher_remarks, r.class_teacher_remarks, r.asst_headmaster_remarks, r.status])
    log_action(user, 'DOWNLOAD_RESULTS', 'exam_results', student.id, request)
    return response
