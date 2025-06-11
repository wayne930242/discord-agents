#!/bin/sh

set -e  # Exit on any error

echo "🚀 Starting Discord Agents..."

# Set Playwright environment for Docker
export PLAYWRIGHT_BROWSERS_PATH=/app/browsers
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Playwright settings for Docker environment
export PLAYWRIGHT_CHROMIUM_ARGS="--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-renderer-backgrounding"

# Wait for dependencies (optional, can be removed if not needed)
echo "⏳ Checking system readiness..."

# Check if Playwright browser is available
if [ ! -d "/app/browsers" ]; then
    echo "❌ Playwright browsers not found, attempting to install..."
    playwright install chromium --with-deps || {
        echo "⚠️  Playwright install failed, continuing anyway..."
    }
fi

# Set memory limits for Node.js processes if needed
export NODE_OPTIONS="--max-old-space-size=1024"

echo "✅ System ready, starting FastAPI application..."

# Run FastAPI app with proper error handling
exec uvicorn discord_agents.fastapi_main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --no-access-log \
    --workers 1 \
    --timeout-keep-alive 30
