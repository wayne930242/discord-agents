from discord_agents.app import create_app
from discord_agents.models.bot import db
from flask_migrate import Migrate  # type: ignore

app = create_app()
migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run()
