"""Utility functions for logging audit events."""
import logging
from .models import AuditLog

logger = logging.getLogger('sms')


def get_client_ip(request):
    if request is None:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(user, action, table_name, record_id, request=None,
               old_values=None, new_values=None):
    """Central audit logger. Call this from every mutating view."""
    try:
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        username = user.username if user else 'anonymous'

        log = AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            username=username,
            action=action,
            table_name=table_name,
            record_id=record_id or 0,
            old_values=old_values or {},
            new_values=new_values or {},
            ip_address=ip,
            user_agent=ua,
        )

        # Also write to file-based log
        logger.info(f"AUDIT [{log.id}] {username} {action} {table_name}#{record_id} ip={ip}")
        return log
    except Exception as e:
        logger.error(f"Audit log failure: {e}")
        return None
