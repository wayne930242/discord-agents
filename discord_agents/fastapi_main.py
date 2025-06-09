from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from discord_agents.api import auth, bots, health, admin
from discord_agents.core.database import engine, Base
from discord_agents.core.config import settings
from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.worker import bot_manager
import os

logger = get_logger("fastapi_main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events"""
    # Startup
    try:
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

# Serve static files (React build)
static_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "dist"
)
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    logger.info(f"Serving static files from: {static_dir}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "discord_agents.fastapi_main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        log_level="info",
    )
