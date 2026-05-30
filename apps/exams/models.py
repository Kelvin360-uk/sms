from django.db import models
from django.conf import settings
from decimal import Decimal


class ExamSession(models.Model):
    """An exam period e.g. 'First Term 2025'."""
    name = models.CharField(max_length=100, unique=True)
    academic_year = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    submission_deadline = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ExamResult(models.Model):
    """Single exam result for one student in one subject."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft (Teacher)'),
        ('SUBMITTED', 'Submitted to Class Teacher'),
        ('CLASS_TEACHER_REVIEWED', 'Class Teacher Reviewed'),
        ('FINAL', 'Finalized (Asst Headmaster)'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='exam_results')
    subject = models.ForeignKey('classes.Subject', on_delete=models.PROTECT)
    exam_session = models.ForeignKey(ExamSession, on_delete=models.PROTECT)
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.PROTECT, related_name='submitted_results')

    score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'))
    grade = models.CharField(max_length=5, blank=True)

    teacher_remarks = models.TextField(blank=True)
    class_teacher_remarks = models.TextField(blank=True)
    class_teacher_signature = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                                  null=True, blank=True, related_name='class_teacher_signed')
    class_teacher_signed_at = models.DateTimeField(null=True, blank=True)

    asst_headmaster_remarks = models.TextField(blank=True)
    asst_headmaster_signature = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                                    null=True, blank=True, related_name='asst_hm_signed')
    asst_headmaster_signed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')

    # Optimistic locking
    version = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('student', 'subject', 'exam_session')]
        indexes = [
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['teacher', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.subject.code} ({self.exam_session.name})"

    def calculate_grade(self):
        """Simple grade calculation - customize per school."""
        pct = (self.score / self.max_score) * 100 if self.max_score else 0
        if pct >= 80: self.grade = 'A'
        elif pct >= 70: self.grade = 'B'
        elif pct >= 60: self.grade = 'C'
        elif pct >= 50: self.grade = 'D'
        elif pct >= 40: self.grade = 'E'
        else: self.grade = 'F'
        return self.grade


class ExamReminder(models.Model):
    """Asst Headmaster sets reminders for teachers about deadlines."""
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=200)
    message = models.TextField()
    deadline = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    target_role = models.CharField(max_length=20, default='TEACHER')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (deadline {self.deadline})"
