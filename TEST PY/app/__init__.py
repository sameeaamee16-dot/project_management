import click
from flask import Flask

from app.config import Config
from app.extensions import db, login_manager
from app.models import User
from app.routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    register_blueprints(app)
    register_cli_commands(app)

    with app.app_context():
        db.create_all()

    return app


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


def register_cli_commands(app: Flask):
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username: str, password: str):
        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo("User already exists.")
            return

        admin = User(username=username, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo("Admin user created successfully.")
