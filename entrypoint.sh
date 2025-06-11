#!/bin/sh

# Run FastAPI app directly (Playwright already installed during build)
exec uvicorn discord_agents.fastapi_main:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log
