#!/usr/bin/env python3
"""
Logging configuration for DHSILED Edge Computing
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime

def setup_logging(grid_id: str, config_level: str = "INFO", 
                  log_file: str = None, console: bool = True) -> logging.Logger:
    """
    Setup comprehensive logging for the edge processor
    
    Args:
        grid_id: Grid identifier for log naming
        config_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, uses default)
        console: Whether to output to console
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger(f"DHSILED_{grid_id}")
    logger.setLevel(getattr(logging, config_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file is None:
        log_file = f"data/logs/edge_processor_{grid_id}_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Rotating file handler (10MB per file, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler (separate file for errors)
    error_log_file = log_file.replace('.log', '_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # Log startup message
    logger.info("=" * 80)
    logger.info(f"DHSILED Edge Processor Logging Initialized for Grid {grid_id}")
    logger.info(f"Log Level: {config_level.upper()}")
    logger.info(f"Log File: {log_file}")
    logger.info("=" * 80)
    
    return logger


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Format the message
        result = super().format(record)
        
        # Reset levelname for other handlers
        record.levelname = levelname
        
        return result