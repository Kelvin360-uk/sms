from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'username', 'action', 'table_name', 'record_id', 'ip_address', 'synced_to_cloud')
    list_filter = ('action', 'table_name', 'synced_to_cloud')
    search_fields = ('username', 'action', 'table_name')
    readonly_fields = [f.name for f in AuditLog._meta.fields]
