from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import AuditLog
from apps.users.permissions import role_required


@role_required('IT_ADMIN', 'HEADMASTER')
def audit_log_list(request):
    qs = AuditLog.objects.select_related('user').all()

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(action__icontains=q) | Q(table_name__icontains=q))

    action = request.GET.get('action')
    if action:
        qs = qs.filter(action=action)

    table = request.GET.get('table')
    if table:
        qs = qs.filter(table_name=table)

    paginator = Paginator(qs, 100)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'audit/list.html', {
        'page': page,
        'q': q,
        'actions': AuditLog.objects.values_list('action', flat=True).distinct()[:50],
        'tables': AuditLog.objects.values_list('table_name', flat=True).distinct()[:50],
    })
