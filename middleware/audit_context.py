"""Stores request in thread-local for use by audit signals if needed."""
import threading

_local = threading.local()


def get_current_request():
    return getattr(_local, 'request', None)


def get_current_user():
    req = get_current_request()
    if req and hasattr(req, 'user') and req.user.is_authenticated:
        return req.user
    return None


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            response = self.get_response(request)
        finally:
            _local.request = None
        return response
