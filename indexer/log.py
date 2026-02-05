"""Logging configuration for """

import logging
import sys
from typing import Optional

from config import Config


def setup_logging(config: Optional[Config] = None, log_level: Optional[str] = None) -> None:
    """Configure Python logging.

    Args:
        config: Config object (uses log_level from config if provided)
        log_level: Override log level (takes precedence over config)
    """
    level_str = log_level or (config.log_level if config else "INFO")
    
    # Map string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(level_str.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("web3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)

