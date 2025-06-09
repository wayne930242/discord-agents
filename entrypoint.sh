#!/bin/sh

# Playwright install
playwright install

# Run FastAPI app (migrations run automatically on startup)
exec uvicorn discord_agents.fastapi_main:app --host 0.0.0.0 --port ${PORT:-8000}
