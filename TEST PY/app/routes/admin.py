from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import Notification, Project, Subtask, Task, User
from app.utils import (
    NotificationService,
    TASK_SEVERITIES,
    TASK_STATUSES,
    role_required,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def parse_date(value: str):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()
    severity = request.args.get("severity", "", type=str).strip()
    project_id = request.args.get("project_id", "", type=str).strip()

    query = Task.query.join(Project).outerjoin(User, Task.assigned_to == User.id)

    if search:
        query = query.filter(
            or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
                Project.name.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.filter(Task.status == status)
    if severity:
        query = query.filter(Task.severity == severity)
    if project_id.isdigit():
        query = query.filter(Task.project_id == int(project_id))

    pagination = query.order_by(Task.due_date.is_(None), Task.due_date.asc()).paginate(
        page=page,
        per_page=8,
        error_out=False,
    )

    today = date.today()
    tomorrow = today + timedelta(days=1)

    stats = {
        "total_projects": Project.query.count(),
        "completed_tasks": Task.query.filter(Task.status == "Completed").count(),
        "pending_tasks": Task.query.filter(Task.status != "Completed").count(),
        "overdue_tasks": Task.query.filter(
            Task.status != "Completed", Task.due_date.isnot(None), Task.due_date < today
        ).count(),
        "no_deadline_tasks": Task.query.filter(Task.due_date.is_(None)).count(),
        "due_tomorrow_tasks": Task.query.filter(
            Task.status != "Completed",
            Task.due_date.isnot(None),
            Task.due_date == tomorrow,
        ).count(),
    }

    projects = Project.query.order_by(Project.created_at.desc()).all()
    users = User.query.order_by(User.username.asc()).all()
    latest_notifications = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        projects=projects,
        users=users,
        task_pagination=pagination,
        today=today,
        filters={
            "search": search,
            "status": status,
            "severity": severity,
            "project_id": project_id,
        },
        task_statuses=TASK_STATUSES,
        task_severities=TASK_SEVERITIES,
        notifications=latest_notifications,
    )


@admin_bp.route("/projects/create", methods=["POST"])
@login_required
@role_required("admin")
def create_project():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Project name is required.", "danger")
        return redirect(url_for("admin.dashboard"))

    project = Project(
        name=name,
        description=request.form.get("description", "").strip(),
        start_date=parse_date(request.form.get("start_date")),
        end_date=parse_date(request.form.get("end_date")),
    )
    db.session.add(project)
    db.session.commit()
    flash("Project created successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/projects/<int:project_id>/edit", methods=["POST"])
@login_required
@role_required("admin")
def edit_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    project.name = request.form.get("name", project.name).strip()
    project.description = request.form.get("description", project.description).strip()
    project.start_date = parse_date(request.form.get("start_date")) or project.start_date
    project.end_date = parse_date(request.form.get("end_date")) or project.end_date
    db.session.commit()
    flash("Project updated successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted successfully.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/tasks/create", methods=["POST"])
@login_required
@role_required("admin")
def create_task():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Task title is required.", "danger")
        return redirect(url_for("admin.dashboard"))

    assigned_to = request.form.get("assigned_to")
    start_date = parse_date(request.form.get("start_date"))
    due_date = parse_date(request.form.get("due_date"))
    if not start_date:
        flash("Task start date is required.", "danger")
        return redirect(url_for("admin.dashboard"))
    if due_date and due_date < start_date:
        flash("Due date cannot be before start date.", "danger")
        return redirect(url_for("admin.dashboard"))

    project_id = int(request.form.get("project_id"))
    project = Project.query.get_or_404(project_id)

    if start_date < project.start_date or start_date > project.end_date:
        flash("Task start date must be within the selected project's timeline.", "danger")
        return redirect(url_for("admin.dashboard"))
    if due_date and (due_date < project.start_date or due_date > project.end_date):
        flash("Task due date must be within the selected project's timeline.", "danger")
        return redirect(url_for("admin.dashboard"))

    task = Task(
        project_id=project_id,
        assigned_to=int(assigned_to) if assigned_to else None,
        title=title,
        description=request.form.get("description", "").strip(),
        severity=request.form.get("severity", "Low"),
        status=request.form.get("status", "Not Started"),
        start_date=start_date,
        due_date=due_date,
    )
    db.session.add(task)
    db.session.commit()

    if task.assigned_to:
        NotificationService.notify_assignment(task, actor_username=current_user.username)
    flash("Task created successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/tasks/<int:task_id>/edit", methods=["POST"])
@login_required
@role_required("admin")
def edit_task(task_id: int):
    task = Task.query.get_or_404(task_id)
    old_assignee = task.assigned_to

    assigned_to = request.form.get("assigned_to")
    start_date = parse_date(request.form.get("start_date"))
    due_date = parse_date(request.form.get("due_date"))
    if start_date is None:
        start_date = task.start_date
    if due_date and due_date < start_date:
        flash("Due date cannot be before start date.", "danger")
        return redirect(url_for("admin.dashboard"))

    project_id = int(request.form.get("project_id", task.project_id))
    project = Project.query.get_or_404(project_id)
    if start_date < project.start_date or start_date > project.end_date:
        flash("Task start date must be within the selected project's timeline.", "danger")
        return redirect(url_for("admin.dashboard"))
    if due_date and (due_date < project.start_date or due_date > project.end_date):
        flash("Task due date must be within the selected project's timeline.", "danger")
        return redirect(url_for("admin.dashboard"))

    task.project_id = project_id
    task.assigned_to = int(assigned_to) if assigned_to else None
    task.title = request.form.get("title", task.title).strip()
    task.description = request.form.get("description", task.description).strip()
    task.severity = request.form.get("severity", task.severity)
    task.status = request.form.get("status", task.status)
    task.start_date = start_date
    task.due_date = due_date
    db.session.commit()

    if task.assigned_to and task.assigned_to != old_assignee:
        NotificationService.notify_assignment(task, actor_username=current_user.username)

    flash("Task updated successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_task(task_id: int):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted successfully.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/subtasks/create", methods=["POST"])
@login_required
@role_required("admin")
def create_subtask():
    title = request.form.get("title", "").strip()
    task_id = request.form.get("task_id", type=int)
    if not title or not task_id:
        flash("Subtask title and parent task are required.", "danger")
        return redirect(url_for("admin.dashboard"))

    parent_task = Task.query.get_or_404(task_id)
    due_date = parse_date(request.form.get("due_date"))
    project = parent_task.project

    if due_date and (due_date < project.start_date or due_date > project.end_date):
        flash("Subtask due date must be within the parent project's timeline.", "danger")
        return redirect(url_for("admin.dashboard"))
    if due_date and due_date < parent_task.start_date:
        flash("Subtask due date cannot be before parent task start date.", "danger")
        return redirect(url_for("admin.dashboard"))
    if due_date and parent_task.due_date and due_date > parent_task.due_date:
        flash("Subtask due date cannot be after parent task due date.", "danger")
        return redirect(url_for("admin.dashboard"))

    subtask = Subtask(
        task_id=task_id,
        title=title,
        status=request.form.get("status", "Not Started"),
        due_date=due_date,
    )
    db.session.add(subtask)
    db.session.commit()
    flash("Subtask created successfully.", "success")
    return redirect(url_for("admin.dashboard"))
