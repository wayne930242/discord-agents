from gunicorn.app.base import BaseApplication
from typing import Any, Dict, Optional
from flask import Flask
from discord_agents.app import create_app
from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.tasks import dispatch_start_all_bots_task
from discord_agents.scheduler.broker import BotRedisClient

logger = get_logger("main")


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


if __name__ == "__main__":
    redis_client = BotRedisClient()
    redis_client.reset_all_bots_status()
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
    dispatch_start_all_bots_task.delay()
    GunicornApp(app, options).run()
