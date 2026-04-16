from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Notification
from app.utils import NotificationService

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/notifications/poll")
@login_required
def poll_notifications():
    NotificationService.sync_deadline_notifications_for_user(current_user.id)
    notifications = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )
    return jsonify(
        {
            "count": len(notifications),
            "notifications": [
                {
                    "id": item.id,
                    "message": item.message,
                    "type": item.type,
                    "created_at": item.created_at.strftime("%Y-%m-%d %H:%M"),
                }
                for item in notifications
            ],
        }
    )


@api_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_as_read(notification_id: int):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    notification.is_read = True
    db.session.commit()
    return jsonify({"message": "Notification marked as read"})


@api_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_as_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"})
