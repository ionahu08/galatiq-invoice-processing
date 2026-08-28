"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path


def setup_logging(log_dir: Path, debug: bool = False) -> None:
    """
    Configure logging for the application.

    Args:
        log_dir: Directory to store log files
        debug: Enable debug-level logging
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = logging.DEBUG if debug else logging.INFO

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(detailed_formatter)

    # File handler (all levels)
    log_file = log_dir / "invoice_processing.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress verbose logs from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
