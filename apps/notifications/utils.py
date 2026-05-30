"""Helper functions to create notifications."""
from .models import Notification


def notify_user(user, title, message, link=''):
    if not user:
        return None
    return Notification.objects.create(recipient=user, title=title, message=message, link=link)


def notify_role(role, title, message, link=''):
    """Send a notification to all active users of a given role."""
    from apps.users.models import User
    users = User.objects.filter(role=role, is_active=True)
    notifications = [
        Notification(recipient=u, title=title, message=message, link=link)
        for u in users
    ]
    Notification.objects.bulk_create(notifications)
    return len(notifications)


def notify_exam_uploaded(exam_result, by_user):
    """Notify IT Admin and Headmaster when a teacher uploads an exam result."""
    title = "Exam Result Uploaded"
    msg = (f"{by_user.get_full_name() or by_user.username} uploaded a result for "
           f"{exam_result.student.full_name} in {exam_result.subject.code} "
           f"(score: {exam_result.score})")
    link = f'/exams/student/{exam_result.student.id}/results/'
    notify_role('IT_ADMIN', title, msg, link)
    notify_role('HEADMASTER', title, msg, link)
