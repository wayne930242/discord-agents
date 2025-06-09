#!/bin/sh

# Playwright install
playwright install

# Run FastAPI app directly
exec uvicorn discord_agents.fastapi_main:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log
