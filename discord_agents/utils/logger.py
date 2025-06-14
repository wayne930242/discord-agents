import logging
import sys
import os
from typing import Union

# ANSI escape sequences for colored log level names
RESET = "\x1b[0m"
LEVEL_COLORS = {
    logging.DEBUG: "\x1b[90m",
    logging.INFO: "\x1b[32m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[41m",
}

# Global variable to track if logging has been configured
_logging_configured = False


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelno, RESET)
        record.levelname = f"{color}{record.levelname}{RESET}"
        return super().format(record)


def setup_custom_logging() -> None:
    """Setup custom logging, override FastAPI/uvicorn's configuration"""
    global _logging_configured

    # Avoid duplicate setup
    if _logging_configured:
        return

    # Get root logger and clear all handlers
    root_logger = logging.getLogger()

    # Clear all existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Get log level from environment variable, default to INFO
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Set root logger level to configurable level
    root_logger.setLevel(log_level)

    log_fmt = "%(asctime)s - %(levelname)s - %(message)s (%(name)s)"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # Console handler - use configurable log level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    if console_handler.stream.isatty():
        formatter: Union[ColoredFormatter, logging.Formatter] = ColoredFormatter(
            log_fmt, datefmt=date_fmt
        )
    else:
        formatter = logging.Formatter(log_fmt, datefmt=date_fmt)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler - keep DEBUG level for file logging
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, "discord_agents.log"), encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_fmt, datefmt=date_fmt))
    root_logger.addHandler(file_handler)

    # Set third-party library log levels to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Reduce Discord.py debug logs
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    # Reduce LiteLLM debug logs
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)

    # Reduce httpcore/httpx debug logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Reduce other common noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Get logger with specified name"""
    global _logging_configured

    logger = logging.getLogger(name)

    # 如果全域 logging 已經設定，直接返回 logger（依賴 root logger 的 handler）
    if _logging_configured:
        return logger

    # 如果全域 logging 尚未設定且此 logger 沒有 handler，建立基本設定
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # 設定 propagate 為 False，避免與 root logger 重複
        logger.propagate = False

        log_fmt = "%(asctime)s - %(levelname)s - %(message)s (%(name)s)"
        date_fmt = "%Y-%m-%d %H:%M:%S"

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        if console_handler.stream.isatty():
            formatter: Union[ColoredFormatter, logging.Formatter] = ColoredFormatter(
                log_fmt, datefmt=date_fmt
            )
        else:
            formatter = logging.Formatter(log_fmt, datefmt=date_fmt)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(
            os.path.join(log_dir, "discord_agents.log"), encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_fmt, datefmt=date_fmt))
        logger.addHandler(file_handler)

    return logger
