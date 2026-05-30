from django.db import models
from django.conf import settings


class Message(models.Model):
    """Internal message — typically to/from IT Admin."""
    CATEGORY_CHOICES = [
        ('ACCESS_REQUEST', 'Access Request'),
        ('PROBLEM', 'Problem / Issue'),
        ('ENROLLMENT_REQUEST', 'Enrollment Request'),
        ('GENERAL', 'General'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, related_name='sent_messages')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='received_messages',
                                   help_text="Leave blank to send to all IT Admins")
    recipient_role = models.CharField(max_length=20, blank=True,
                                       help_text="Send to all users of this role")

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='GENERAL')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='NORMAL')
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')

    attachment = models.FileField(upload_to='messages/', blank=True, null=True)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='resolved_messages')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['recipient', 'status']),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.subject}"
