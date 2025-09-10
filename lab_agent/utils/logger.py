import logging
import sys
from typing import Optional
from datetime import datetime


def setup_logger(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger("lab_agent")
    
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance for the given name"""
    if name is None:
        name = "lab_agent"
    elif not name.startswith("lab_agent"):
        name = f"lab_agent.{name}"
    
    logger = logging.getLogger(name)
    
    # If no handlers, set up basic configuration
    if not logger.handlers and not logging.getLogger("lab_agent").handlers:
        setup_logger()
    
    return logger