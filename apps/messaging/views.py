from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as flash
from django.utils import timezone
from django.db.models import Q

from .models import Message
from apps.users.models import User
from apps.audit.utils import log_action
from apps.notifications.utils import notify_user, notify_role


@login_required
def inbox(request):
    user = request.user
    qs = Message.objects.filter(
        Q(recipient=user) | Q(recipient_role=user.role) | Q(recipient__isnull=True, recipient_role='')
    ).select_related('sender').order_by('-created_at')

    # IT Admin sees all unassigned messages
    if user.is_it_admin:
        qs = Message.objects.filter(
            Q(recipient=user) | Q(recipient_role='IT_ADMIN') |
            Q(recipient__isnull=True, recipient_role='')
        ).select_related('sender').order_by('-created_at')

    return render(request, 'messaging/inbox.html', {'messages_list': qs[:200]})


@login_required
def sent(request):
    qs = Message.objects.filter(sender=request.user).order_by('-created_at')
    return render(request, 'messaging/sent.html', {'messages_list': qs[:200]})


@login_required
def compose(request):
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id') or None
        recipient_role = request.POST.get('recipient_role', '')

        msg = Message(
            sender=request.user,
            recipient_id=recipient_id,
            recipient_role=recipient_role,
            category=request.POST.get('category', 'GENERAL'),
            priority=request.POST.get('priority', 'NORMAL'),
            subject=request.POST['subject'],
            body=request.POST['body'],
        )
        if 'attachment' in request.FILES:
            msg.attachment = request.FILES['attachment']
        msg.save()

        log_action(request.user, 'SEND_MESSAGE', 'messages', msg.id, request,
                   new_values={'subject': msg.subject, 'category': msg.category})

        # Notify recipient(s)
        if msg.recipient:
            notify_user(msg.recipient, f"New message: {msg.subject}", msg.body[:200],
                        link=f'/messaging/{msg.id}/')
        elif recipient_role:
            notify_role(recipient_role, f"New message: {msg.subject}", msg.body[:200],
                        link=f'/messaging/{msg.id}/')
        else:
            # Default to IT Admin
            notify_role('IT_ADMIN', f"New message: {msg.subject}", msg.body[:200],
                        link=f'/messaging/{msg.id}/')

        flash.success(request, "Message sent.")
        return redirect('inbox')

    # Pre-fill default recipient = IT Admin
    return render(request, 'messaging/compose.html', {
        'users': User.objects.filter(is_active=True).order_by('username'),
        'categories': Message.CATEGORY_CHOICES,
        'priorities': Message.PRIORITY_CHOICES,
        'roles': User.Role.choices,
    })


@login_required
def message_detail(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    user = request.user

    # Access: sender, recipient, or matching role
    allowed = (msg.sender == user or msg.recipient == user or
               msg.recipient_role == user.role or
               (user.is_it_admin and msg.recipient_role == 'IT_ADMIN'))
    if not allowed:
        flash.error(request, "Access denied.")
        return redirect('inbox')

    replies = msg.replies.all().order_by('created_at') if not msg.parent else msg.parent.replies.all().order_by('created_at')
    return render(request, 'messaging/detail.html', {'msg': msg, 'replies': replies})


@login_required
def reply_message(request, message_id):
    original = get_object_or_404(Message, id=message_id)
    if request.method == 'POST':
        reply = Message.objects.create(
            sender=request.user,
            recipient=original.sender,
            category=original.category,
            priority=original.priority,
            subject=f"Re: {original.subject}",
            body=request.POST['body'],
            parent=original.parent or original,
        )
        log_action(request.user, 'REPLY_MESSAGE', 'messages', reply.id, request)
        notify_user(original.sender, f"Reply: {original.subject}", reply.body[:200],
                    link=f'/messaging/{reply.id}/')
        flash.success(request, "Reply sent.")
        return redirect('message_detail', message_id=reply.id)
    return redirect('message_detail', message_id=message_id)


@login_required
def resolve_message(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    if not (request.user.is_it_admin or msg.recipient == request.user):
        flash.error(request, "Cannot resolve this message.")
        return redirect('message_detail', message_id=message_id)

    msg.status = 'RESOLVED'
    msg.resolved_by = request.user
    msg.resolved_at = timezone.now()
    msg.save()
    log_action(request.user, 'RESOLVE_MESSAGE', 'messages', msg.id, request)
    if msg.sender:
        notify_user(msg.sender, f"Message resolved: {msg.subject}",
                    f"Your message has been marked resolved.")
    flash.success(request, "Message marked as resolved.")
    return redirect('inbox')
