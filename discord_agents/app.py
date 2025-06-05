import os
from typing import Any
from flask import Flask, redirect, url_for, request
from flask_admin import Admin, AdminIndexView
from discord_agents.env import DATABASE_URL, SECRET_KEY
from discord_agents.utils.logger import get_logger
from discord_agents.models.bot import db, BotModel, NoteModel
from discord_agents.view.bot_config_view import BotConfigView
from discord_agents.view.bot_manage_view import BotManageView
from discord_agents.utils.auth import requires_auth, check_auth, authenticate
from discord_agents.scheduler.worker import bot_manager

logger = get_logger("app")


class SecureAdminIndexView(AdminIndexView):
    """Custom AdminIndexView with authentication"""

    def is_accessible(self) -> bool:
        """Check if the current user is authenticated"""
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return False
        return check_auth(auth.username, auth.password)

    def inaccessible_callback(self, name: str, **kwargs: Any):  # type: ignore
        """Redirect to authentication if not accessible"""
        return authenticate()


def init_db(app: Flask) -> None:
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Database initialized successfully")


def init_admin(app: Flask) -> None:
    logger.info("Initializing admin interface...")
    admin = Admin(
        app,
        name="Discord Agents",
        template_mode="bootstrap4",
        index_view=SecureAdminIndexView(),
    )
    admin.add_view(BotConfigView(BotModel, db.session))
    admin.add_view(BotManageView(name="Bot Manage", endpoint="botmanageview"))
    logger.info("Admin interface initialized")


def create_app() -> Flask:
    try:
        logger.info("Creating Flask application...")
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SECRET_KEY"] = SECRET_KEY

        bot_manager.start()
        logger.info("BotManager monitor thread started.")

        @app.route("/health")
        def health_check() -> tuple[str, int]:
            return "OK", 200

        @app.route("/")
        @requires_auth
        def index():  # type: ignore
            return redirect(url_for("admin.index"))

        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "discord_agents",
            "view",
            "templates",
        )
        app.template_folder = template_dir
        logger.info(f"Template directory set to: {template_dir}")

        init_db(app)
        init_admin(app)

        logger.info("Flask application created successfully")
        return app

    except Exception as e:
        logger.error(f"Error creating Flask application: {str(e)}", exc_info=True)
        raise
