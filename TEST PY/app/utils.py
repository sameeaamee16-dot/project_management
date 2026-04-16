from datetime import date, datetime, timedelta
from functools import wraps

from flask import abort
from flask_login import current_user

from app.extensions import db
from app.models import Notification, Task

TASK_STATUSES = ["Not Started", "In Progress", "Completed"]
TASK_SEVERITIES = ["Low", "Medium", "High"]


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return func(*args, **kwargs)

        return wrapped

    return decorator


class NotificationService:
    @staticmethod
    def create_notification(user_id: int, message: str, type_name: str) -> None:
        notification = Notification(user_id=user_id, message=message, type=type_name)
        db.session.add(notification)
        db.session.commit()

    @staticmethod
    def notify_assignment(task: Task, actor_username: str = "System") -> None:
        if task.assigned_to is None:
            return
        message = (
            f"Task assigned: '{task.title}' in project '{task.project.name}' by {actor_username}."
        )
        NotificationService.create_notification(task.assigned_to, message, "assignment")

    @staticmethod
    def _exists_today(user_id: int, message: str, type_name: str) -> bool:
        start_of_day = datetime.combine(date.today(), datetime.min.time())
        return (
            Notification.query.filter(
                Notification.user_id == user_id,
                Notification.type == type_name,
                Notification.message == message,
                Notification.created_at >= start_of_day,
            ).count()
            > 0
        )

    @staticmethod
    def sync_deadline_notifications_for_user(user_id: int) -> None:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        tasks = Task.query.filter(
            Task.assigned_to == user_id,
            Task.status != "Completed",
        ).all()

        for task in tasks:
            if task.due_date is None:
                continue

            if task.due_date == tomorrow:
                message = f"Reminder: Task '{task.title}' is due tomorrow ({task.due_date})."
                if not NotificationService._exists_today(user_id, message, "reminder"):
                    db.session.add(
                        Notification(user_id=user_id, message=message, type="reminder")
                    )

            if task.due_date < today:
                message = f"Overdue warning: Task '{task.title}' was due on {task.due_date}."
                if not NotificationService._exists_today(user_id, message, "overdue"):
                    db.session.add(
                        Notification(user_id=user_id, message=message, type="overdue")
                    )

        db.session.commit()
