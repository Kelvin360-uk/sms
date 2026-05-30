from django.contrib import admin
from .models import ExamSession, ExamResult, ExamReminder

admin.site.register(ExamSession)
admin.site.register(ExamReminder)


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'exam_session', 'score', 'grade', 'status', 'teacher')
    list_filter = ('status', 'exam_session', 'subject')
    search_fields = ('student__full_name', 'student__student_id')
