import os
from dotenv import load_dotenv
from typing import Any

from discord_agents.utils.logger import get_logger

logger = get_logger("env")

load_dotenv()

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/agent_data.db")

DM_ID_WHITE_LIST: list[str] = os.getenv("DM_ID_WHITE_LIST", "").split(",")
SERVER_ID_WHITE_LIST: list[str] = os.getenv("SERVER_ID_WHITE_LIST", "").split(",")

GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gemini-2.5-flash-preview-04-17")

SECRET_KEY: str = os.getenv("SECRET_KEY", "")

ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "")

REQUIRED_ENV_VARS: dict[str, Any] = {
    "DATABASE_URL": DATABASE_URL,
    "GOOGLE_API_KEY": GOOGLE_API_KEY,
    "TAVILY_API_KEY": TAVILY_API_KEY,
    "REDIS_URL": REDIS_URL,
}

missing_vars: list[str] = []
for var_name, value in REQUIRED_ENV_VARS.items():
    if value is None:
        missing_vars.append(var_name)

if missing_vars:
    error_message = (
        f"Error: Required environment variables are missing: {', '.join(missing_vars)}. "
        "Please check your .env file or system environment variable settings."
    )
    raise EnvironmentError(error_message)

logger.info("--- Discord Agents environment settings loaded successfully ---")
logger.info("------------------------------------")
