from django.db import models
from django.conf import settings
from decimal import Decimal


class PaymentLedger(models.Model):
    """Immutable post-approval payment record.
    Edits allowed only while status in (PENDING_FINANCE, PENDING_IT).
    After APPROVED, only reversals (new entries linking back via reversal_of)."""

    PAYMENT_METHODS = [
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
    ]

    STATUS_CHOICES = [
        ('PENDING_FINANCE', 'Pending Finance Approval'),
        ('PENDING_IT', 'Pending IT Admin Approval'),
        ('APPROVED', 'Approved (Final)'),
        ('REJECTED', 'Rejected'),
        ('REVERSED', 'Reversed'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='payment_ledger_entries')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True, help_text="For mobile money or bank transfer")
    payment_date = models.DateTimeField()
    academic_year = models.CharField(max_length=10)
    semester = models.CharField(max_length=20, blank=True)

    # Notes file (auto-named: studentname_studentid_timestamp.txt)
    note_file = models.FileField(upload_to='payment_notes/', blank=True, null=True)
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    cheque_image = models.ImageField(upload_to='receipts/cheques/', blank=True, null=True)

    # Finance approval (temporary)
    finance_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                       related_name='finance_approved_payments')
    finance_approved_at = models.DateTimeField(auto_now_add=True)
    finance_notes = models.TextField(blank=True)

    # Headmaster/Asst Headmaster approval (for cash/cheque)
    hm_approval_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name='hm_approved_payments')
    hm_approved_at = models.DateTimeField(null=True, blank=True)
    hm_signature_image = models.ImageField(upload_to='receipts/signatures/', blank=True, null=True)

    # IT Admin approval (permanent)
    it_admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='it_approved_payments')
    it_admin_approved_at = models.DateTimeField(null=True, blank=True)
    it_admin_notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_FINANCE')
    rejection_reason = models.TextField(blank=True)

    # Immutable reversal pattern
    reversal_of = models.ForeignKey('self', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='reversed_by')
    reversal_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['academic_year']),
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.amount_paid} ({self.get_status_display()})"

    @property
    def is_immutable(self):
        return self.status in ('APPROVED', 'REVERSED', 'REJECTED')

    @property
    def note_filename(self):
        """Filename per spec: student_name_student_id_timestamp"""
        safe_name = self.student.full_name.replace(' ', '_')
        return f"{safe_name}_{self.student.student_id}_{self.created_at.strftime('%Y%m%d%H%M%S')}.txt"

    def generate_note_content(self):
        """Generate the textual note that accompanies the payment."""
        return f"""PAYMENT NOTE
============================
Student Name: {self.student.full_name}
Student ID: {self.student.student_id}
Amount Paid: {self.amount_paid}
Payment Method: {self.get_payment_method_display()}
Transaction ID: {self.transaction_id or 'N/A'}
Payment Date: {self.payment_date}
Academic Year: {self.academic_year}
Semester: {self.semester or 'N/A'}

Finance Officer: {self.finance_user.get_full_name() or self.finance_user.username}
Finance Approved At: {self.finance_approved_at}
Finance Notes: {self.finance_notes or '-'}

Headmaster/Asst HM Approval: {self.hm_approval_user.get_full_name() if self.hm_approval_user else 'N/A'}
HM Approved At: {self.hm_approved_at or 'N/A'}

IT Admin Final Approval: {self.it_admin_user.get_full_name() if self.it_admin_user else 'PENDING'}
IT Admin Approved At: {self.it_admin_approved_at or 'PENDING'}

Status: {self.get_status_display()}
============================
"""
