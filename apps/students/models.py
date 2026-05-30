from django.db import models
from decimal import Decimal


class Student(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]

    student_id = models.CharField(max_length=30, unique=True, db_index=True)
    full_name = models.CharField(max_length=200, db_index=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    residence = models.CharField(max_length=200)

    parent_guardian_name = models.CharField(max_length=200)
    parent_guardian_phone = models.CharField(max_length=20)
    parent_guardian_email = models.EmailField(blank=True)
    parent_guardian_relation = models.CharField(max_length=50, default='Guardian')

    current_class = models.ForeignKey('classes.SchoolClass', on_delete=models.SET_NULL,
                                      null=True, related_name='students')
    admission_date = models.DateField(auto_now_add=True)
    photo = models.ImageField(upload_to='profiles/students/', blank=True, null=True)

    # Fee tracking
    total_fees_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_fees_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    outstanding_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['full_name']),
            models.Index(fields=['current_class']),
            models.Index(fields=['gender']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

    def recalculate_balance(self):
        """Calculate balance from approved payments."""
        from apps.payments.models import PaymentLedger
        paid = PaymentLedger.objects.filter(
            student=self, status='APPROVED'
        ).aggregate(total=models.Sum('amount_paid'))['total'] or Decimal('0.00')
        self.total_fees_paid = paid
        self.outstanding_balance = self.total_fees_due - paid
        self.save(update_fields=['total_fees_paid', 'outstanding_balance'])
        return self.outstanding_balance
