"""
logger.py
=========
Structured JSON logger for Samiksha.

Usage:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("Something happened", extra={"tool": "open_browser"})

Every log record includes:
    timestamp, level, module, message, and any extra fields you pass.
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger

from config.settings import settings


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger configured to write JSON to the log file
    and human-readable output to the console.

    Args:
        name: Usually __name__ of the calling module.

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(settings.log_level)

    # ----------------------------------------------------------
    # Console handler — human-readable for development
    # ----------------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)
    console_fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    # ----------------------------------------------------------
    # File handler — structured JSON for production/analysis
    # ----------------------------------------------------------
    file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
    file_handler.setLevel(settings.log_level)
    json_fmt = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    file_handler.setFormatter(json_fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Don't propagate to root logger to avoid double output
    logger.propagate = False

    return logger
