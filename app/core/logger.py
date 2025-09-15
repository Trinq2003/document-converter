"""
Logging configuration and utilities
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from app.config import settings, dir_manager


class Logger:
    """Centralized logging configuration"""
    
    def __init__(self, name: str = "document_converter"):
        self.name = name
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger with file and console handlers"""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, settings.log_level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handlers (only if logs directory exists)
        try:
            # Ensure logs directory exists
            dir_manager.logs_dir.mkdir(parents=True, exist_ok=True)
            
            # File handler
            log_file = dir_manager.logs_dir / "document_converter.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Error file handler
            error_log_file = dir_manager.logs_dir / "errors.log"
            error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            logger.addHandler(error_handler)
            
        except (OSError, PermissionError) as e:
            # If we can't create file handlers, just use console logging
            logger.warning(f"Could not setup file logging: {e}. Using console logging only.")
        
        return logger
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger


# Global logger instance
logger = Logger().get_logger()
