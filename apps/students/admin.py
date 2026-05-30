from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'full_name', 'gender', 'current_class', 'outstanding_balance', 'is_active')
    list_filter = ('gender', 'current_class', 'is_active')
    search_fields = ('student_id', 'full_name', 'parent_guardian_name')
