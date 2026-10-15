from .models import Notification


def notifications(request):

    if not request.user.is_authenticated:
        return {
            "unread_notifications_count": 0,
            "notifications": [],
        }

    user_notifications = Notification.objects.filter(
        user=request.user
    ).order_by(
        "-created_at"
    )

    unread_count = user_notifications.filter(
        is_read=False
    ).count()

    return {
        "unread_notifications_count": unread_count,
        "notifications": user_notifications[:8],
    }