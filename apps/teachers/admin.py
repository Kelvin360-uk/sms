from django.contrib import admin
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'full_name', 'gender', 'is_class_teacher', 'assigned_class', 'is_active')
    list_filter = ('gender', 'is_class_teacher', 'staff_type', 'is_active')
    search_fields = ('employee_id', 'full_name', 'email', 'phone')
    filter_horizontal = ('subjects_taught', 'classes_taught')
