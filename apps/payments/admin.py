from django.contrib import admin
from .models import PaymentLedger


@admin.register(PaymentLedger)
class PaymentLedgerAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount_paid', 'payment_method', 'status', 'created_at', 'finance_user', 'it_admin_user')
    list_filter = ('status', 'payment_method', 'academic_year')
    search_fields = ('student__full_name', 'student__student_id', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at', 'reversal_of')
