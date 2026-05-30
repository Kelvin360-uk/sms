"""Enforces role-based session expiry. Teachers: 120 min by default; Admins: 240."""
from datetime import timedelta
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.utils import timezone


EXEMPT_PATHS = {'login', 'logout', 'request_renewal'}


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Determine URL name
            try:
                url_name = resolve(request.path_info).url_name
            except Resolver404:
                url_name = None

            if url_name not in EXEMPT_PATHS:
                user = request.user
                if user.session_expires_at and timezone.now() >= user.session_expires_at:
                    user.is_active_session = False
                    user.must_renew_session = True
                    user.save(update_fields=['is_active_session', 'must_renew_session'])
                    logout(request)
                    messages.warning(request,
                        "Your session has expired. Teachers must see IT Admin to renew.")
                    return redirect('login')

                # Sliding refresh for admin/headmaster level only
                if user.is_admin_level and user.session_expires_at:
                    remaining = user.session_expires_at - timezone.now()
                    if remaining < timedelta(minutes=30):
                        user.session_expires_at = timezone.now() + timedelta(minutes=user.session_minutes)
                        user.save(update_fields=['session_expires_at'])

        return self.get_response(request)
