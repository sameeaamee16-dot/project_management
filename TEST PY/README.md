# Project Management Web Application

Full-stack Project Management system with role-based dashboards for Admin and User.

## Tech Stack
- Backend: Flask, SQLAlchemy ORM, MySQL
- Frontend: HTML, CSS, JavaScript
- Authentication: Session-based auth with Flask-Login
- Password Security: Werkzeug hashing

## Features

### Authentication
- Register and Login
- Roles: `admin`, `user`
- Session-based protected routes

### Admin Dashboard
- Project CRUD
- Task CRUD with assignment to users
- Subtask creation under tasks
- Analytics cards:
  - Total projects
  - Completed tasks
  - Pending tasks
- Search, filters, and pagination on task list

### User Dashboard
- View assigned projects
- View assigned tasks and subtasks
- Update status workflow:
  - `Not Started -> In Progress -> Completed`
- Add remarks/comments on tasks

### Notifications (Polling)
- Assignment notifications
- Reminder notifications (1 day before due date)
- Overdue notifications
- Mark one or all notifications as read

## Folder Structure
```text
TEST PY/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── utils.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── api.py
│   │   ├── auth.py
│   │   └── user.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/main.js
│   └── templates/
│       ├── base.html
│       ├── auth/
│       │   ├── login.html
│       │   └── register.html
│       ├── admin/dashboard.html
│       └── user/dashboard.html
├── database/
│   └── schema.sql
├── .env.example
├── requirements.txt
└── run.py
```

## Setup Instructions

1. Create virtual environment and install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create MySQL database and tables:
```bash
mysql -u root -p < database/schema.sql
```

If you already created tables earlier, run this migration once to allow tasks without a deadline:
```sql
ALTER TABLE tasks MODIFY due_date DATE NULL;
```

3. Configure environment:
```bash
copy .env.example .env
```
Update `.env` values for MySQL credentials and secret key.

4. Run the app:
```bash
python run.py
```

5. Create admin user:
```bash
flask --app run.py create-admin
```

6. Open:
- `http://127.0.0.1:5000`

## Notes
- SQLAlchemy models are configured with foreign keys using `ON DELETE CASCADE`.
- Notifications are simulated in near real-time via polling every 20 seconds.
- UI is responsive for desktop and mobile with a dashboard-style layout.
