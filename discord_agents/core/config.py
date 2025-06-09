from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/agent_data.db")

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Admin credentials
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin")

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # Migration settings
    auto_migrate: bool = True

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Discord whitelist
    dm_id_white_list: str = os.getenv("DM_ID_WHITE_LIST", "")
    server_id_white_list: str = os.getenv("SERVER_ID_WHITE_LIST", "")

    # API Keys
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    xai_api_key: str = os.getenv("XAI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Agent model
    agent_model: str = os.getenv("AGENT_MODEL", "gemini-2.5-flash-preview-04-17")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

    @property
    def dm_id_white_list_parsed(self) -> list[str]:
        """Parse DM ID whitelist"""
        return [id.strip() for id in self.dm_id_white_list.split(",") if id.strip()]

    @property
    def server_id_white_list_parsed(self) -> list[str]:
        """Parse server ID whitelist"""
        return [id.strip() for id in self.server_id_white_list.split(",") if id.strip()]


settings = Settings()
