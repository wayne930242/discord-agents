import os
from gunicorn.app.base import BaseApplication
from typing import Any, Dict, Optional
from flask import Flask, redirect, url_for, request, Response
from flask_admin import Admin
from functools import wraps

from discord_agents.scheduler.bot_runner import BotRunner
from discord_agents.domain.models import db, Bot
from discord_agents.view.bot_view import BotAgentView
from discord_agents.view.runner_view import BotManagementView
from discord_agents.env import DATABASE_URL
from discord_agents.env import ADMIN_PASSWORD, ADMIN_USERNAME
from discord_agents.utils.logger import get_logger

logger = get_logger("main")


def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def authenticate():
    return Response(
        "Could not verify your access level for that URL.\n"
        "You have to login with proper credentials",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'},
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


class GunicornApp(BaseApplication):
    def __init__(self, app: Flask, options: Optional[Dict[str, Any]] = None) -> None:
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        for key, value in self.options.items():
            self.cfg.set(key, value)

    def load(self) -> Flask:
        return self.application


def create_app() -> Flask:
    try:
        logger.info("Creating Flask application...")
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SECRET_KEY"] = "your-secret-key"

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

        db.init_app(app)
        with app.app_context():
            db.create_all()
            logger.info("Database initialized successfully")

        logger.info("Initializing BotRunner...")
        bot_runner = BotRunner()
        app.bot_runner = bot_runner
        logger.info("BotRunner initialized")

        with app.app_context():
            logger.info("Registering bots from database...")
            bots = Bot.query.all()
            for bot in bots:
                try:
                    logger.info(f"Registering bot_{bot.id}...")
                    bot_runner.register_bot(f"bot_{bot.id}", bot.to_bot())
                    logger.info(f"Bot_{bot.id} registered successfully")
                except Exception as e:
                    logger.error(
                        f"Failed to register bot_{bot.id}: {str(e)}", exc_info=True
                    )

        try:
            bot_runner.start_all_bots()
            logger.info("All bots started successfully")
        except Exception as e:
            logger.error(f"Failed to start all bots: {str(e)}", exc_info=True)

        logger.info("Initializing admin interface...")
        admin = Admin(app, name="Discord Agents", template_mode="bootstrap4")
        admin.add_view(BotAgentView(Bot, db.session))
        admin.add_view(BotManagementView(name="Runner", endpoint="botmanagementview"))
        logger.info("Admin interface initialized")

        logger.info("Flask application created successfully")
        return app

    except Exception as e:
        logger.error(f"Error creating Flask application: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    options = {
        "bind": "%s:%s" % ("0.0.0.0", "8080"),
        "worker_class": "gthread",
        "workers": 1,
        "threads": 4,
        "timeout": 120,
        "accesslog": "-",
        "errorlog": "-",
        "loglevel": "info",
    }

    app = create_app()
    GunicornApp(app, options).run()
