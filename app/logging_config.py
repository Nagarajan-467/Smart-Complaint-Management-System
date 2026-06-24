"""
Smart Complaint Management System
Logging configuration with file and console handlers.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config import get_settings


def setup_logging() -> logging.Logger:
    """
    Configure application-wide logging with:
    - Console handler (stdout) for development visibility
    - Rotating file handler to prevent unbounded log growth
    - Structured format with timestamps, level, module, and message

    Returns:
        The root application logger.
    """
    settings = get_settings()

    # Ensure the logs directory exists
    log_dir = os.path.dirname(settings.log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Create the application logger
    logger = logging.getLogger("smart_complaint")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.DEBUG))

    # Prevent duplicate handlers on reload
    if logger.handlers:
        return logger

    # Log format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(module)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (rotating: 5 MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        filename=settings.log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("Logging initialized — level=%s, file=%s", settings.log_level, settings.log_file)
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger under the application namespace.

    Args:
        name: The sub-logger name (typically __name__).

    Returns:
        A child logger instance.
    """
    return logging.getLogger(f"smart_complaint.{name}")
