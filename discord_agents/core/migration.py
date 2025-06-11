from pathlib import Path
from alembic import command
from alembic.config import Config
from discord_agents.utils.logger import get_logger

logger = get_logger("migration")


def get_alembic_config() -> Config:
    """Get Alembic config"""
    project_root = Path(__file__).parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"Alembic config not found: {alembic_ini_path}")

    config = Config(str(alembic_ini_path))
    return config


def check_migration_needed() -> bool:
    """Check if migration is needed"""
    try:
        config = get_alembic_config()

        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from discord_agents.core.database import engine

        script_dir = ScriptDirectory.from_config(config)

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            head_rev = script_dir.get_current_head()

            logger.info(f"Current revision: {current_rev}")
            logger.info(f"Head revision: {head_rev}")

            return current_rev != head_rev

    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return True


def run_migrations() -> bool:
    """Run database migrations"""
    try:
        logger.info("Starting database migrations...")
        config = get_alembic_config()

        command.upgrade(config, "head")
        logger.info("✅ Database migrations completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def auto_migrate() -> None:
    """Auto migrate (called when application starts)"""
    from discord_agents.core.config import settings

    if not settings.auto_migrate:
        logger.info("🔄 Auto migration disabled by configuration")
        return

    try:
        if check_migration_needed():
            logger.info("🔄 Database migration needed, running migrations...")
            success = run_migrations()
            if not success:
                logger.error("❌ Migration failed, application may not work correctly")
        else:
            logger.info("✅ Database is up to date, no migration needed")

    except Exception as e:
        logger.error(f"❌ Auto migration error: {e}")


def create_migration(message: str) -> bool:
    """Create new migration file"""
    try:
        logger.info(f"Creating migration: {message}")
        config = get_alembic_config()

        command.revision(config, autogenerate=True, message=message)
        logger.info("✅ Migration created successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create migration: {e}")
        return False
