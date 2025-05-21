#!/bin/sh

# Db migrate
flask db upgrade

# Run app
exec python -m discord_agents.main
