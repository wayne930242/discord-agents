#!/bin/sh

# Playwright install
playwright install

# Db migrate
flask db upgrade

# Run app
exec python -m discord_agents.main
