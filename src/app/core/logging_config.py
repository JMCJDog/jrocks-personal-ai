"""Logging Configuration - Centralized secure logging setup.

Provides a standard logging configuration that defaults to INFO level
to prevent accidental leakage of sensitive data in debug logs.
"""

import logging
import sys
from pathlib import Path

def setup_logging(
    log_level: int = logging.INFO,
    log_file: str = "app.log"
) -> None:
    """Configure logging for the application.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Log file path
    """
    # Create logs directory
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    
    # Basic configuration
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path / log_file, encoding='utf-8')
        ]
    )
    
    # Quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    
    logging.info("Logging initialized securely (INFO level)")
