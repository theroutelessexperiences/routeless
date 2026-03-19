import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from marketplace.models import Notification
from django.contrib.auth.models import User

def send_realtime_notification(user_id, title, message, link=""):
    """
    Creates a Notification record and broadcasts it via WebSocket to the user.
    """
    # Create DB record
    try:
        user = User.objects.get(id=user_id)
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            link=link
        )
        
        # Broadcast via Channels
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"notify_{user_id}",
                {
                    "type": "user.notification",
                    "notification": {
                        "id": notification.id,
                        "title": notification.title,
                        "message": notification.message,
                        "link": notification.link,
                        "created_at": notification.created_at.strftime("%b. %d, %Y, %I:%M %p")
                    }
                }
            )
        return notification
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
        return None
