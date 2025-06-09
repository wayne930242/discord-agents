#!/usr/bin/env python3
"""
Database migration management script
Used to manage the migration from Flask-SQLAlchemy to pure SQLAlchemy
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: str) -> int:
    """Execute command and return exit code"""
    print(f"🔄 Execute: {cmd}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def check_migration_status():
    """Check migration status"""
    print("📋 Check migration status...")
    return run_command("alembic current")


def create_migration(message: str):
    """Create new migration"""
    print(f"📝 Create migration: {message}")
    return run_command(f'alembic revision --autogenerate -m "{message}"')


def upgrade_database():
    """Upgrade database to latest version"""
    print("⬆️ Upgrade database...")
    return run_command("alembic upgrade head")


def downgrade_database(revision: str = "-1"):
    """Downgrade database"""
    print(f"⬇️ Downgrade database to: {revision}")
    return run_command(f"alembic downgrade {revision}")


def show_history():
    """Show migration history"""
    print("📚 Migration history:")
    return run_command("alembic history --verbose")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print(
            """
🗄️ Database migration management tool

用法:
    python migrate.py <command> [args]

命令:
    status          - Check current migration status
    create <msg>    - Create new migration
    upgrade         - Upgrade database to latest version
    downgrade [rev] - Downgrade database (default: -1)
    history         - Show migration history

範例:
    python migrate.py status
    python migrate.py create "Add new column"
    python migrate.py upgrade
    python migrate.py downgrade -1
    python migrate.py history
        """
        )
        return 1

    command = sys.argv[1]

    if command == "status":
        return check_migration_status()

    elif command == "create":
        if len(sys.argv) < 3:
            print("❌ Please provide migration message")
            return 1
        message = " ".join(sys.argv[2:])
        return create_migration(message)

    elif command == "upgrade":
        return upgrade_database()

    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return downgrade_database(revision)

    elif command == "history":
        return show_history()

    else:
        print(f"❌ Unknown command: {command}")
        return 1


if __name__ == "__main__":
    exit(main())
