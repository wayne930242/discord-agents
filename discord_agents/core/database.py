from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from discord_agents.core.config import settings
from discord_agents.models.bot import Base

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    ),
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
