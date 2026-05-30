from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role-based access for SMS."""

    class Role(models.TextChoices):
        IT_ADMIN = 'IT_ADMIN', 'IT Administrator'
        HEADMASTER = 'HEADMASTER', 'Headmaster / Director'
        ASST_HEADMASTER = 'ASST_HEADMASTER', 'Assistant Headmaster'
        CLASS_TEACHER = 'CLASS_TEACHER', 'Class Teacher'
        TEACHER = 'TEACHER', 'Teacher'
        FINANCE = 'FINANCE', 'Finance'
        HR = 'HR', 'Human Resources'

    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=20, blank=True)
    residence = models.CharField(max_length=200, blank=True)
    is_active_session = models.BooleanField(default=False)
    session_expires_at = models.DateTimeField(null=True, blank=True)
    must_renew_session = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # ---- Role checks ---------------------------------------------------------
    @property
    def is_it_admin(self):
        return self.role == self.Role.IT_ADMIN

    @property
    def is_headmaster(self):
        return self.role == self.Role.HEADMASTER

    @property
    def is_asst_headmaster(self):
        return self.role == self.Role.ASST_HEADMASTER

    @property
    def is_class_teacher(self):
        return self.role == self.Role.CLASS_TEACHER

    @property
    def is_teacher(self):
        return self.role in (self.Role.TEACHER, self.Role.CLASS_TEACHER)

    @property
    def is_finance(self):
        return self.role == self.Role.FINANCE

    @property
    def is_hr(self):
        return self.role == self.Role.HR

    @property
    def is_admin_level(self):
        """Headmaster, Asst Headmaster, IT Admin."""
        return self.role in (
            self.Role.IT_ADMIN,
            self.Role.HEADMASTER,
            self.Role.ASST_HEADMASTER,
        )

    @property
    def can_view_all(self):
        return self.role in (
            self.Role.IT_ADMIN,
            self.Role.HEADMASTER,
            self.Role.ASST_HEADMASTER,
        )

    @property
    def can_edit_data(self):
        """Only IT Admin and teachers can edit data."""
        return self.role in (
            self.Role.IT_ADMIN,
            self.Role.TEACHER,
            self.Role.CLASS_TEACHER,
        )

    @property
    def can_download_data(self):
        """Only IT Admin can download by default."""
        return self.role == self.Role.IT_ADMIN

    @property
    def session_minutes(self):
        """Session duration based on role."""
        from django.conf import settings
        if self.is_teacher:
            return settings.TEACHER_SESSION_MINUTES
        return settings.ADMIN_SESSION_MINUTES


class DownloadPermission(models.Model):
    """IT Admin grants temporary download permissions to teachers."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_permissions')
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_downloads')
    resource_type = models.CharField(max_length=50)  # e.g. 'exam_results'
    resource_id = models.IntegerField(null=True, blank=True)  # specific record, or null for all
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} -> {self.resource_type} (until {self.expires_at})"


class SessionRenewalRequest(models.Model):
    """Teacher requests session renewal from IT Admin."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DENIED', 'Denied'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='renewal_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_renewals')
    handled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} renewal request ({self.status})"
