import os
from flask import Flask, redirect, url_for
from flask_admin import Admin
from discord_agents.env import DATABASE_URL, SECRET_KEY
from discord_agents.utils.logger import get_logger
from discord_agents.models.bot import db, BotModel
from discord_agents.view.bot_config_view import BotConfigView
from discord_agents.view.bot_manage_view import BotManageView
from discord_agents.utils.auth import requires_auth
from discord_agents.scheduler.worker import bot_manager

logger = get_logger("app")


def init_db(app: Flask):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Database initialized successfully")


def init_admin(app: Flask):
    logger.info("Initializing admin interface...")
    admin = Admin(app, name="Discord Agents", template_mode="bootstrap4")
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
        def health_check():
            return "OK", 200

        @app.route("/")
        @requires_auth
        def index():
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
