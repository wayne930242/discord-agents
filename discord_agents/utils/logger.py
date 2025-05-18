import logging
import sys

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

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        fmt = '%(asctime)s - %(levelname)s - %(message)s (%(name)s)'
        datefmt = '%Y-%m-%d %H:%M:%S'
        if console_handler.stream.isatty():
            formatter = ColoredFormatter(fmt, datefmt=datefmt)
        else:
            formatter = logging.Formatter(fmt, datefmt=datefmt)

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

