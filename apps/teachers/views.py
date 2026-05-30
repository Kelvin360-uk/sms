from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
import csv

from .models import Teacher
from apps.classes.models import SchoolClass, Subject
from apps.users.models import User
from apps.users.permissions import it_admin_required, staff_view_required
from apps.audit.utils import log_action
from django.utils import timezone


@staff_view_required
def teacher_list(request):
    qs = Teacher.objects.filter(is_active=True).select_related('user', 'assigned_class')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(employee_id__icontains=q))

    gender = request.GET.get('gender')
    if gender in ('M', 'F'):
        qs = qs.filter(gender=gender)

    return render(request, 'teachers/list.html', {
        'teachers': qs,
        'total_male': qs.filter(gender='M').count(),
        'total_female': qs.filter(gender='F').count(),
        'total': qs.count(),
        'q': q,
    })


@it_admin_required
def create_teacher(request):
    if request.method == 'POST':
        try:
            # Create User first
            user = User.objects.create_user(
                username=request.POST['username'],
                password=request.POST['password'],
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                email=request.POST['email'],
                phone=request.POST['phone'],
                residence=request.POST['residence'],
                role=request.POST['role'],
            )
            teacher = Teacher.objects.create(
                user=user,
                employee_id=request.POST['employee_id'],
                full_name=request.POST['full_name'],
                gender=request.POST['gender'],
                residence=request.POST['residence'],
                phone=request.POST['phone'],
                email=request.POST['email'],
                date_of_birth=request.POST.get('date_of_birth') or None,
                staff_type=request.POST.get('staff_type', 'TEACHING'),
                is_class_teacher=(request.POST['role'] == 'CLASS_TEACHER'),
                assigned_class_id=request.POST.get('assigned_class') or None,
            )

            if 'subjects' in request.POST:
                teacher.subjects_taught.set(request.POST.getlist('subjects'))
            if 'classes' in request.POST:
                teacher.classes_taught.set(request.POST.getlist('classes'))

            log_action(request.user, 'CREATE_TEACHER', 'teachers', teacher.id, request,
                       new_values={'employee_id': teacher.employee_id, 'name': teacher.full_name})
            messages.success(request, f"Teacher {teacher.full_name} added.")
            return redirect('teacher_list')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'teachers/create.html', {
        'classes': SchoolClass.objects.filter(is_active=True),
        'subjects': Subject.objects.all(),
        'roles': [('TEACHER', 'Teacher'), ('CLASS_TEACHER', 'Class Teacher')],
    })


@staff_view_required
def teacher_detail(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    return render(request, 'teachers/detail.html', {'teacher': teacher})


@it_admin_required
def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    old_values = {f: str(getattr(teacher, f)) for f in
                  ['full_name', 'phone', 'email', 'residence', 'is_class_teacher']}

    if request.method == 'POST':
        teacher.full_name = request.POST['full_name']
        teacher.phone = request.POST['phone']
        teacher.email = request.POST['email']
        teacher.residence = request.POST['residence']
        teacher.staff_type = request.POST.get('staff_type', teacher.staff_type)
        teacher.is_class_teacher = (request.POST.get('is_class_teacher') == 'on')
        if request.POST.get('assigned_class'):
            teacher.assigned_class_id = request.POST['assigned_class']
        teacher.save()

        if 'subjects' in request.POST:
            teacher.subjects_taught.set(request.POST.getlist('subjects'))
        if 'classes' in request.POST:
            teacher.classes_taught.set(request.POST.getlist('classes'))

        new_values = {f: str(getattr(teacher, f)) for f in
                      ['full_name', 'phone', 'email', 'residence', 'is_class_teacher']}
        log_action(request.user, 'EDIT_TEACHER', 'teachers', teacher.id, request,
                   old_values=old_values, new_values=new_values)
        messages.success(request, "Teacher updated.")
        return redirect('teacher_detail', teacher_id=teacher.id)

    return render(request, 'teachers/edit.html', {
        'teacher': teacher,
        'classes': SchoolClass.objects.filter(is_active=True),
        'subjects': Subject.objects.all(),
    })


@it_admin_required
def export_teachers(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="teachers_{timezone.now().date()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Full Name', 'Gender', 'Email', 'Phone', 'Residence',
                     'Staff Type', 'Class Teacher Of'])
    for t in Teacher.objects.filter(is_active=True).select_related('assigned_class'):
        writer.writerow([t.employee_id, t.full_name, t.gender, t.email, t.phone,
                         t.residence, t.staff_type,
                         t.assigned_class.name if t.assigned_class else ''])
    log_action(request.user, 'EXPORT_TEACHERS', 'teachers', 0, request)
    return response
