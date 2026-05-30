from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Every action taken in the system is logged here."""
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('LOGIN_FAILED', 'Failed Login'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('EXPORT', 'Export'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='audit_logs')
    username = models.CharField(max_length=150, blank=True)  # cache in case user deleted
    action = models.CharField(max_length=50, db_index=True)
    table_name = models.CharField(max_length=100, db_index=True)
    record_id = models.IntegerField(default=0)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Cloud sync flag
    synced_to_cloud = models.BooleanField(default=False, db_index=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['table_name', '-timestamp']),
            models.Index(fields=['synced_to_cloud']),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.username or 'anonymous'} :: {self.action} on {self.table_name}"
