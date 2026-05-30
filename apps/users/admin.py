from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, DownloadPermission, SessionRenewalRequest


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'is_active_session', 'session_expires_at')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('SMS Profile', {'fields': ('role', 'phone', 'residence', 'profile_picture',
                                     'is_active_session', 'session_expires_at', 'must_renew_session')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('SMS Profile', {'fields': ('role', 'phone', 'residence', 'email')}),
    )


admin.site.register(DownloadPermission)
admin.site.register(SessionRenewalRequest)
