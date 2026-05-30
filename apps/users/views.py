from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, Q

from .models import User, SessionRenewalRequest, DownloadPermission
from .permissions import it_admin_required, role_required
from apps.students.models import Student
from apps.teachers.models import Teacher
from apps.exams.models import ExamResult
from apps.payments.models import PaymentLedger
from apps.notifications.models import Notification
from apps.audit.utils import log_action


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account is disabled.")
                return render(request, 'auth/login.html')

            # Set session expiration based on role
            user.session_expires_at = timezone.now() + timedelta(minutes=user.session_minutes)
            user.is_active_session = True
            user.must_renew_session = False
            user.save(update_fields=['session_expires_at', 'is_active_session', 'must_renew_session'])

            login(request, user)
            log_action(user, 'LOGIN', 'users', user.id, request, new_values={'username': user.username})
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials.")
            # Audit failed login (no user, but log attempt)
            log_action(None, 'LOGIN_FAILED', 'users', 0, request, new_values={'attempted_username': username})

    return render(request, 'auth/login.html')


@login_required
def dashboard(request):
    """Role-specific dashboard."""
    user = request.user
    context = {'user': user}

    if user.is_it_admin or user.is_headmaster or user.is_asst_headmaster:
        context.update({
            'total_students': Student.objects.filter(is_active=True).count(),
            'total_boys': Student.objects.filter(is_active=True, gender='M').count(),
            'total_girls': Student.objects.filter(is_active=True, gender='F').count(),
            'total_teachers': Teacher.objects.filter(is_active=True).count(),
            'total_male_staff': Teacher.objects.filter(is_active=True, gender='M').count(),
            'total_female_staff': Teacher.objects.filter(is_active=True, gender='F').count(),
            'pending_payments': PaymentLedger.objects.filter(status='PENDING_IT').count(),
            'recent_exams': ExamResult.objects.order_by('-created_at')[:10],
            'unread_notifications': Notification.objects.filter(recipient=user, is_read=False).count(),
        })

    elif user.is_teacher or user.is_class_teacher:
        try:
            teacher = user.teacher_profile
            context['teacher'] = teacher
            context['my_classes'] = teacher.classes_taught.all()
            context['recent_exams'] = ExamResult.objects.filter(teacher=teacher).order_by('-created_at')[:10]
            if user.is_class_teacher and teacher.assigned_class:
                context['my_class_students'] = Student.objects.filter(
                    current_class=teacher.assigned_class, is_active=True
                )
        except Teacher.DoesNotExist:
            messages.warning(request, "No teacher profile linked to your account. Contact IT Admin.")

    elif user.is_finance or user.is_hr:
        context.update({
            'total_students': Student.objects.filter(is_active=True).count(),
            'total_teachers': Teacher.objects.filter(is_active=True).count(),
            'total_male_staff': Teacher.objects.filter(is_active=True, gender='M').count(),
            'total_female_staff': Teacher.objects.filter(is_active=True, gender='F').count(),
            'pending_payments': PaymentLedger.objects.filter(status='PENDING_FINANCE').count(),
            'students_with_balance': Student.objects.filter(is_active=True, outstanding_balance__gt=0).count(),
        })

    return render(request, 'dashboard/index.html', context)


@login_required
def request_session_renewal(request):
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        SessionRenewalRequest.objects.create(user=request.user, reason=reason)
        log_action(request.user, 'REQUEST_RENEWAL', 'session_renewal_requests', 0, request)
        messages.success(request, "Renewal request submitted to IT Admin.")
        logout(request)
        return redirect('login')
    return render(request, 'auth/session_renewal.html')


@it_admin_required
def handle_renewal_requests(request):
    pending = SessionRenewalRequest.objects.filter(status='PENDING').order_by('-requested_at')
    return render(request, 'users/renewal_requests.html', {'requests': pending})


@it_admin_required
def renewal_action(request, req_id, action):
    req = get_object_or_404(SessionRenewalRequest, id=req_id)
    if action == 'approve':
        req.status = 'APPROVED'
        req.user.must_renew_session = False
        req.user.session_expires_at = timezone.now() + timedelta(minutes=req.user.session_minutes)
        req.user.save(update_fields=['must_renew_session', 'session_expires_at'])
    elif action == 'deny':
        req.status = 'DENIED'
    req.handled_by = request.user
    req.handled_at = timezone.now()
    req.save()
    log_action(request.user, f'RENEWAL_{action.upper()}', 'session_renewal_requests', req.id, request)
    messages.success(request, f"Renewal request {action}d.")
    return redirect('handle_renewals')


@it_admin_required
def user_list(request):
    users = User.objects.all().order_by('role', 'username')
    return render(request, 'users/list.html', {'users': users})


@it_admin_required
def create_user(request):
    if request.method == 'POST':
        try:
            user = User.objects.create_user(
                username=request.POST['username'],
                password=request.POST['password'],
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                email=request.POST.get('email', ''),
                phone=request.POST.get('phone', ''),
                residence=request.POST.get('residence', ''),
                role=request.POST['role'],
            )
            log_action(request.user, 'CREATE_USER', 'users', user.id, request,
                       new_values={'username': user.username, 'role': user.role})
            messages.success(request, f"User {user.username} created.")
            return redirect('user_list')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'users/create.html', {'roles': User.Role.choices})


@it_admin_required
def grant_download_permission(request):
    """Grant a teacher temporary download access."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=request.POST['user_id'])
        resource_type = request.POST['resource_type']
        hours = int(request.POST.get('hours', 24))
        perm = DownloadPermission.objects.create(
            user=target_user,
            granted_by=request.user,
            resource_type=resource_type,
            expires_at=timezone.now() + timedelta(hours=hours),
        )
        log_action(request.user, 'GRANT_DOWNLOAD', 'download_permissions', perm.id, request,
                   new_values={'target_user': target_user.username, 'resource_type': resource_type})
        messages.success(request, f"Download access granted to {target_user.username} for {hours}h.")
        return redirect('user_list')

    teachers = User.objects.filter(role__in=['TEACHER', 'CLASS_TEACHER'])
    return render(request, 'users/grant_download.html', {'teachers': teachers})
