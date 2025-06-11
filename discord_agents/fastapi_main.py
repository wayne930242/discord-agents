from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from discord_agents.api import auth, bots, health, admin, token_usage
from discord_agents.core.database import engine, Base
from discord_agents.core.config import settings
from discord_agents.utils.logger import get_logger, setup_custom_logging
from discord_agents.scheduler.worker import bot_manager
import os
from fastapi.responses import FileResponse, Response

logger = get_logger("fastapi_main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events"""
    # Startup
    try:
        # Reset logging format, because uvicorn may overwrite it
        setup_custom_logging()

        logger.info("Starting Discord Agents FastAPI application...")

        # Initialize database with automatic migrations
        from discord_agents.core.migration import auto_migrate

        auto_migrate()

        # Ensure tables exist (fallback)
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")

        # Start bot manager
        bot_manager.start()
        logger.info("BotManager monitor thread started")

        # Auto-start all bots from database
        try:
            from discord_agents.core.database import get_db
            from discord_agents.services.bot_service import BotService

            db = next(get_db())
            try:
                result = BotService.start_all_bots(db)
                logger.info(
                    f"🚀 Auto-started bots: {result['started']}/{result['total']} successful, {result['failed']} failed"
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error auto-starting bots: {str(e)}", exc_info=True)

        logger.info("FastAPI application started successfully")

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        raise

    yield

    # Shutdown
    try:
        logger.info("Shutting down Discord Agents FastAPI application...")
        # Add any cleanup logic here
        logger.info("FastAPI application shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)


# Create FastAPI app
app = FastAPI(
    title="Discord Agents API",
    description="Discord Bot Management System with Modern UI",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(bots.router, prefix="/api/v1/bots", tags=["bots"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(
    token_usage.router, prefix="/api/v1/token-usage", tags=["token-usage"]
)

# Serve static files (React build)
static_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "dist"
)
if os.path.exists(static_dir):
    # Create a custom static files handler for SPA
    static_files = StaticFiles(directory=static_dir)

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str) -> Response:
        """Serve SPA for all non-API routes"""
        # Check if it's an API route
        if full_path.startswith("api/"):
            # Let FastAPI handle API routes normally
            raise HTTPException(status_code=404, detail="API endpoint not found")

        # Try to serve static file first
        try:
            return await static_files.get_response(full_path, request.scope)
        except:
            # If file not found, serve index.html for SPA routing
            return FileResponse(os.path.join(static_dir, "index.html"))

    logger.info(f"Serving SPA from: {static_dir}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "discord_agents.fastapi_main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=True,
        log_level="info",
        # Disable uvicorn's access log to avoid overwriting our custom logging format
        access_log=False,
    )
