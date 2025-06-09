"""
FastAPI 資料庫遷移管理模組
在應用啟動時自動處理資料庫遷移
"""

import subprocess
import sys
from pathlib import Path
from alembic import command
from alembic.config import Config
from discord_agents.utils.logger import get_logger

logger = get_logger("migration")


def get_alembic_config() -> Config:
    """獲取 Alembic 配置"""
    # 獲取專案根目錄
    project_root = Path(__file__).parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"Alembic config not found: {alembic_ini_path}")

    config = Config(str(alembic_ini_path))
    return config


def check_migration_needed() -> bool:
    """檢查是否需要遷移"""
    try:
        config = get_alembic_config()

        # 檢查當前版本和最新版本
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
        return True  # 如果無法檢查，假設需要遷移


def run_migrations() -> bool:
    """執行資料庫遷移"""
    try:
        logger.info("Starting database migrations...")
        config = get_alembic_config()

        # 執行遷移
        command.upgrade(config, "head")
        logger.info("✅ Database migrations completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def auto_migrate() -> None:
    """自動遷移（在應用啟動時調用）"""
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
                # 不要停止應用，讓它繼續運行
        else:
            logger.info("✅ Database is up to date, no migration needed")

    except Exception as e:
        logger.error(f"❌ Auto migration error: {e}")
        # 不要停止應用，讓它繼續運行


def create_migration(message: str) -> bool:
    """創建新的遷移檔案"""
    try:
        logger.info(f"Creating migration: {message}")
        config = get_alembic_config()

        command.revision(config, autogenerate=True, message=message)
        logger.info("✅ Migration created successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create migration: {e}")
        return False
