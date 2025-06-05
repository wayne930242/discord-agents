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


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelno, RESET)
        record.levelname = f"{color}{record.levelname}{RESET}"
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_fmt = '%(asctime)s - %(levelname)s - %(message)s (%(name)s)'
    date_fmt = '%Y-%m-%d %H:%M:%S'

    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        if console_handler.stream.isatty():
            formatter: Union[ColoredFormatter, logging.Formatter] = ColoredFormatter(log_fmt, datefmt=date_fmt)
        else:
            formatter = logging.Formatter(log_fmt, datefmt=date_fmt)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "discord_agents.log"), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_fmt, datefmt=date_fmt))
        logger.addHandler(file_handler)

    return logger

