from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import Notification, Project, Task, TaskComment, User
from app.utils import NotificationService, TASK_STATUSES, role_required

user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/dashboard")
@login_required
@role_required("user", "admin")
def dashboard():
    NotificationService.sync_deadline_notifications_for_user(current_user.id)

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()

    query = Task.query.filter(Task.assigned_to == current_user.id)
    if search:
        query = query.join(Project).filter(
            or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
                Project.name.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.filter(Task.status == status)

    pagination = query.order_by(Task.due_date.is_(None), Task.due_date.asc()).paginate(
        page=page,
        per_page=8,
        error_out=False,
    )

    gantt_tasks = (
        Task.query.filter(Task.assigned_to == current_user.id)
        .order_by(Task.start_date.asc())
        .all()
    )
    timeline_end_candidates = [
        (task.due_date or (task.start_date + timedelta(days=1))) for task in gantt_tasks
    ]
    timeline_start = min([task.start_date for task in gantt_tasks], default=date.today())
    timeline_end = max(timeline_end_candidates, default=timeline_start + timedelta(days=1))
    total_days = max((timeline_end - timeline_start).days + 1, 1)

    gantt_data = []
    for task in gantt_tasks:
        bar_end = task.due_date or (task.start_date + timedelta(days=1))
        offset_days = (task.start_date - timeline_start).days
        duration_days = max((bar_end - task.start_date).days + 1, 1)
        gantt_data.append(
            {
                "title": task.title,
                "project_name": task.project.name,
                "status": task.status,
                "start": task.start_date,
                "end": task.due_date,
                "offset_pct": round((offset_days / total_days) * 100, 2),
                "width_pct": round((duration_days / total_days) * 100, 2),
            }
        )

    assigned_projects = (
        Project.query.join(Task)
        .filter(Task.assigned_to == current_user.id)
        .distinct()
        .all()
    )
    latest_notifications = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(8)
        .all()
    )

    stats = {
        "total_projects": len(assigned_projects),
        "completed_tasks": Task.query.filter_by(
            assigned_to=current_user.id, status="Completed"
        ).count(),
        "pending_tasks": Task.query.filter(
            Task.assigned_to == current_user.id, Task.status != "Completed"
        ).count(),
    }

    return render_template(
        "user/dashboard.html",
        task_pagination=pagination,
        assigned_projects=assigned_projects,
        stats=stats,
        notifications=latest_notifications,
        filters={"search": search, "status": status},
        task_statuses=TASK_STATUSES,
        gantt_data=gantt_data,
        timeline_start=timeline_start,
        timeline_end=timeline_end,
    )


@user_bp.route("/tasks/<int:task_id>/status", methods=["POST"])
@login_required
@role_required("user", "admin")
def update_task_status(task_id: int):
    task = Task.query.get_or_404(task_id)
    if task.assigned_to != current_user.id:
        flash("You are not authorized to update this task.", "danger")
        return redirect(url_for("user.dashboard"))

    new_status = request.form.get("status", "").strip()
    status_order = {"Not Started": 0, "In Progress": 1, "Completed": 2}
    if new_status not in status_order:
        flash("Invalid task status provided.", "danger")
        return redirect(url_for("user.dashboard"))

    if status_order[new_status] < status_order[task.status]:
        flash("Task status cannot move backwards.", "warning")
        return redirect(url_for("user.dashboard"))

    task.status = new_status
    db.session.commit()
    flash("Task status updated.", "success")
    return redirect(url_for("user.dashboard"))


@user_bp.route("/tasks/<int:task_id>/comment", methods=["POST"])
@login_required
@role_required("user", "admin")
def add_task_comment(task_id: int):
    task = Task.query.get_or_404(task_id)
    if task.assigned_to != current_user.id:
        flash("You can only comment on your assigned tasks.", "danger")
        return redirect(url_for("user.dashboard"))

    body = request.form.get("body", "").strip()
    if not body:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("user.dashboard"))

    comment = TaskComment(task_id=task.id, user_id=current_user.id, body=body)
    db.session.add(comment)
    db.session.commit()

    snippet = (body[:70] + "...") if len(body) > 70 else body
    message = f"Remark from {current_user.username} on task '{task.title}': {snippet}"[:255]
    admin_users = User.query.filter(User.role == "admin", User.id != current_user.id).all()
    for admin in admin_users:
        NotificationService.create_notification(admin.id, message, "remark")

    flash("Comment added.", "success")
    return redirect(url_for("user.dashboard"))
