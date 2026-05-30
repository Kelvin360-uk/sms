from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'category', 'priority', 'sender', 'recipient', 'status', 'created_at')
    list_filter = ('status', 'category', 'priority')
    search_fields = ('subject', 'body', 'sender__username')
