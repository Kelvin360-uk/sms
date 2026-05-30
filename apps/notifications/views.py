from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(recipient=request.user)
    return render(request, 'notifications/list.html', {'notifications': qs[:200]})


@login_required
def mark_read(request, notif_id):
    n = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    n.is_read = True
    n.save(update_fields=['is_read'])
    if n.link:
        return redirect(n.link)
    return redirect('notification_list')


@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notification_list')
