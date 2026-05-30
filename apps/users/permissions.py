"""Role-based access decorators and permission helpers."""
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """Restrict view to specified roles. Usage: @role_required('IT_ADMIN', 'HEADMASTER')"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, "You don't have permission to access that page.")
                return HttpResponseForbidden("Access denied: insufficient role privileges.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def it_admin_required(view_func):
    return role_required('IT_ADMIN')(view_func)


def admin_level_required(view_func):
    """IT Admin, Headmaster, or Assistant Headmaster."""
    return role_required('IT_ADMIN', 'HEADMASTER', 'ASST_HEADMASTER')(view_func)


def teacher_required(view_func):
    return role_required('TEACHER', 'CLASS_TEACHER')(view_func)


def finance_required(view_func):
    return role_required('FINANCE')(view_func)


def can_view_all_required(view_func):
    return role_required('IT_ADMIN', 'HEADMASTER', 'ASST_HEADMASTER')(view_func)


def staff_view_required(view_func):
    """Roles that can view aggregate staff/student data: IT, HM, AHM, Finance, HR."""
    return role_required('IT_ADMIN', 'HEADMASTER', 'ASST_HEADMASTER', 'FINANCE', 'HR')(view_func)
