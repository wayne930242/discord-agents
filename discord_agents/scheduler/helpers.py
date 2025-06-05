from flask import Flask

flask_app: Flask | None = None


def get_flask_app() -> Flask:
    global flask_app
    if flask_app is None:
        from discord_agents.app import create_app

        flask_app = create_app()
    return flask_app
