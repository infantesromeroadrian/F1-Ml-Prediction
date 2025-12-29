"""Logging configuration for F1 Race Replay application."""

import logging
import sys

from src.config import get_config


def setup_logging(log_level: str | None = None) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Optional log level override. If None, uses config value.
    """
    config = get_config()
    level = log_level or config.log_level

    # Get numeric log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(config.log_format)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()  # Remove any existing handlers
    root_logger.addHandler(console_handler)

    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # If logging hasn't been set up yet, set it up now
    if not logger.handlers and logging.getLogger().handlers:
        # Root logger is configured, this logger will inherit
        pass
    elif not logging.getLogger().handlers:
        # No root logger configured, set it up
        setup_logging()

    return logger


class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emoji prefixes to log messages."""

    EMOJI_MAP = {
        logging.DEBUG: "🐞",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "💥",
    }

    def __init__(self, base_formatter: logging.Formatter, use_emoji: bool = True):
        """
        Initialize emoji formatter.

        Args:
            base_formatter: Base formatter to use for formatting
            use_emoji: Whether to add emoji prefixes
        """
        super().__init__(base_formatter._fmt, base_formatter.datefmt)
        self.base_formatter = base_formatter
        self.use_emoji = use_emoji

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional emoji prefix."""
        if self.use_emoji:
            emoji = self.EMOJI_MAP.get(record.levelno, "")
            if emoji:
                record.msg = f"{emoji} {record.msg}"
        return self.base_formatter.format(record)


def setup_emoji_logging(log_level: str | None = None) -> None:
    """
    Configure logging with emoji prefixes.

    Args:
        log_level: Optional log level override.
    """
    config = get_config()
    level = log_level or config.log_level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Base formatter
    base_formatter = logging.Formatter(config.log_format)

    # Emoji formatter
    formatter = EmojiFormatter(base_formatter, config.use_emoji_prefixes)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.propagate = False
