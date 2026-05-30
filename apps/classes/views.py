from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SchoolClass, Subject
from apps.users.permissions import it_admin_required, can_view_all_required
from apps.audit.utils import log_action


@login_required
def class_list(request):
    classes = SchoolClass.objects.filter(is_active=True).order_by('grade_level', 'section')
    return render(request, 'classes/list.html', {'classes': classes})


@it_admin_required
def create_class(request):
    if request.method == 'POST':
        cls = SchoolClass.objects.create(
            name=request.POST['name'],
            grade_level=request.POST['grade_level'],
            section=request.POST.get('section', ''),
            academic_year=request.POST['academic_year'],
        )
        log_action(request.user, 'CREATE_CLASS', 'school_classes', cls.id, request,
                   new_values={'name': cls.name})
        messages.success(request, f"Class {cls.name} created.")
        return redirect('class_list')
    return render(request, 'classes/create.html')


@can_view_all_required
def class_detail(request, class_id):
    cls = get_object_or_404(SchoolClass, id=class_id)
    students = cls.students.filter(is_active=True)
    return render(request, 'classes/detail.html', {'class': cls, 'students': students})


@login_required
def subject_list(request):
    subjects = Subject.objects.all().order_by('code')
    return render(request, 'classes/subjects.html', {'subjects': subjects})


@it_admin_required
def create_subject(request):
    if request.method == 'POST':
        subj = Subject.objects.create(
            name=request.POST['name'],
            code=request.POST['code'],
            description=request.POST.get('description', ''),
        )
        log_action(request.user, 'CREATE_SUBJECT', 'subjects', subj.id, request)
        messages.success(request, f"Subject {subj.name} created.")
        return redirect('subject_list')
    return render(request, 'classes/create_subject.html')
