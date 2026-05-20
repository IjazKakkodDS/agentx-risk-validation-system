"""
Shared logging factory for AgentX agents and utilities.

Call setup_logger(__name__) once per module. Subsequent calls return the same
logger without adding duplicate handlers.
"""

import logging
import sys
from pathlib import Path

from utils.config import LOG_DIR


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    file_handler = logging.FileHandler(LOG_DIR / "agentx.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
