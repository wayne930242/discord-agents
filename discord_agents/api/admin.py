"""
Admin API endpoints for system management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any
from discord_agents.core.security import get_current_user
from discord_agents.core.migration import check_migration_needed, run_migrations, create_migration
from discord_agents.utils.logger import get_logger

logger = get_logger("admin_api")
router = APIRouter()


class MigrationRequest(BaseModel):
    message: str


class MigrationStatus(BaseModel):
    migration_needed: bool
    current_revision: str | None
    head_revision: str | None


@router.get("/migration/status", response_model=Dict[str, Any])
async def get_migration_status(current_user: str = Depends(get_current_user)):
    """Get current migration status"""
    try:
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from discord_agents.core.database import engine
        from discord_agents.core.migration import get_alembic_config

        config = get_alembic_config()
        script_dir = ScriptDirectory.from_config(config)

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            head_rev = script_dir.get_current_head()

            return {
                "migration_needed": current_rev != head_rev,
                "current_revision": current_rev,
                "head_revision": head_rev,
                "status": "up_to_date" if current_rev == head_rev else "migration_needed"
            }

    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration status: {str(e)}"
        )


@router.post("/migration/upgrade")
async def upgrade_database(current_user: str = Depends(get_current_user)):
    """Manually trigger database upgrade"""
    try:
        logger.info(f"Manual migration triggered by user: {current_user}")

        if not check_migration_needed():
            return {"message": "Database is already up to date", "success": True}

        success = run_migrations()
        if success:
            return {"message": "Migration completed successfully", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Migration failed"
            )

    except Exception as e:
        logger.error(f"Manual migration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )


@router.post("/migration/create")
async def create_new_migration(
    request: MigrationRequest,
    current_user: str = Depends(get_current_user)
):
    """Create a new migration"""
    try:
        logger.info(f"Creating migration '{request.message}' by user: {current_user}")

        success = create_migration(request.message)
        if success:
            return {"message": f"Migration '{request.message}' created successfully", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create migration"
            )

    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create migration: {str(e)}"
        )


@router.get("/system/info")
async def get_system_info(current_user: str = Depends(get_current_user)):
    """Get system information"""
    try:
        from discord_agents.core.config import settings
        from discord_agents.models.bot import BotModel
        from discord_agents.core.database import SessionLocal

        db = SessionLocal()
        try:
            bot_count = db.query(BotModel).count()
        finally:
            db.close()

        return {
            "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "local",
            "auto_migrate": settings.auto_migrate,
            "bot_count": bot_count,
            "cors_origins": settings.cors_origins,
            "admin_user": current_user
        }

    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system info: {str(e)}"
        )
