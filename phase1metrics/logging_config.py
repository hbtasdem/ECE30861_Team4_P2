"""
Centralized logging configuration and utilities.

This module provides a comprehensive logging system with:
- Verbosity levels: 0=silent, 1=informational, 2=debug (default=0)
- File and console output with different formats
- Log rotation and management
- Environment variable configuration (VERBOSITY)
- Structured logging with correlation IDs
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class LogLevel(Enum):
    """Log level enumeration for better type safety."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig:
    """Centralized logging configuration manager."""

    def __init__(self) -> None:
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Verbosity configuration: 0=silent, 1=informational, 2=debug
        self.verbosity = self._get_verbosity_from_env("VERBOSITY", "0")
        self.console_level = self._verbosity_to_log_level(self.verbosity)
        self.file_level = logging.DEBUG  # Always log everything to file
        self.log_format = os.getenv("LOG_FORMAT", "detailed")
        self.max_file_size = int(os.getenv("MAX_LOG_FILE_SIZE", "10485760"))
        self.backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    def _get_verbosity_from_env(self, env_var: str, default: str) -> int:
        """Get verbosity level from environment variable with fallback."""
        verbosity_str = os.getenv(env_var, default)
        try:
            verbosity = int(verbosity_str)
            if verbosity not in [0, 1, 2]:
                raise ValueError(
                    f"Verbosity must be 0, 1, or 2, got {verbosity}")
            return verbosity
        except ValueError:
            return 0  # Default to silent

    def _verbosity_to_log_level(self, verbosity: int) -> int:
        """Convert verbosity level to logging level."""
        if verbosity == 0:
            return logging.CRITICAL + 1  # Silent - no output
        elif verbosity == 1:
            return logging.INFO  # Informational messages
        elif verbosity == 2:
            return logging.DEBUG  # Debug messages
        else:
            return logging.CRITICAL + 1  # Default to silent

    def get_formatter(
        self, format_type: str = "detailed"
    ) -> logging.Formatter:
        """Get appropriate formatter based on type."""
        if format_type == "simple":
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        elif format_type == "detailed":
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        elif format_type == "json":
            return JsonFormatter()
        else:
            return logging.Formatter('%(message)s')

    def setup_logger(self, name: str,
                     correlation_id: Optional[str] = None) -> logging.Logger:
        """Set up a logger with console and file handlers."""
        logger = logging.getLogger(name)
        # Set to lowest level, handlers will filter
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        console_handler.setFormatter(self.get_formatter(self.log_format))
        logger.addHandler(console_handler)

        # File handler with rotation
        log_file = (self.log_dir /
                    f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.file_level)
        file_handler.setFormatter(self.get_formatter("detailed"))
        logger.addHandler(file_handler)

        # Add correlation ID to log records if provided
        if correlation_id:

            def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
                record = old_factory(*args, **kwargs)
                record.correlation_id = correlation_id
                return record
            old_factory = logging.getLogRecordFactory()
            logging.setLogRecordFactory(record_factory)

        return logger


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.filename,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return str(log_entry)


class LoggerManager:
    """Singleton logger manager to ensure consistent logging."""

    _instance: Optional["LoggerManager"] = None
    _loggers: Dict[str, logging.Logger] = {}
    _config: LoggingConfig

    def __new__(cls) -> "LoggerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = LoggingConfig()
        return cls._instance

    def get_logger(self, name: str,
                   correlation_id: Optional[str] = None) -> logging.Logger:
        """Get or create a logger with the given name."""
        # Always recreate config to pick up environment changes
        self._config = LoggingConfig()

        # Clear and recreate logger to apply new configuration
        if name in self._loggers:
            del self._loggers[name]

        self._loggers[name] = self._config.setup_logger(name, correlation_id)
        return self._loggers[name]

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for all future log records."""

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = old_factory(*args, **kwargs)
            record.correlation_id = correlation_id
            return record
        old_factory = logging.getLogRecordFactory()
        logging.setLogRecordFactory(record_factory)


# Global logger manager instance
logger_manager = LoggerManager()


def get_logger(name: str,
               correlation_id: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)
        correlation_id: Optional correlation ID for request tracing

    Returns:
        Configured logger instance
    """
    return logger_manager.get_logger(name, correlation_id)


def set_log_level(level: str) -> None:
    """
    Set the global log level for console output.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level_int = getattr(logging, level.upper(), logging.INFO)
    logger_manager._config.console_level = level_int

    # Update all existing loggers
    for logger in logger_manager._loggers.values():
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level_int)


def log_function_call(func_name: str, args: Optional[Dict[str, Any]] = None,
                      logger: Optional[logging.Logger] = None) -> None:
    """
    Log function call with arguments for debugging.

    Args:
        func_name: Name of the function being called
        args: Dictionary of function arguments
        logger: Logger instance (optional)
    """
    if logger is None:
        logger = get_logger(__name__)

    if args:
        logger.debug(f"Calling {func_name} with args: {args}")
    else:
        logger.debug(f"Calling {func_name}")


def log_performance(operation: str, duration: float,
                    logger: Optional[logging.Logger] = None) -> None:
    """
    Log performance metrics.

    Args:
        operation: Description of the operation
        duration: Duration in seconds
        logger: Logger instance (optional)
    """
    if logger is None:
        logger = get_logger(__name__)

    logger.info(f"Performance: {operation} completed in {duration:.3f}s")


def log_error_with_context(error: Exception, context: str = "",
                           logger: Optional[logging.Logger] = None) -> None:
    """
    Log error with additional context information.

    Args:
        error: Exception instance
        context: Additional context string
        logger: Logger instance (optional)
    """
    if logger is None:
        logger = get_logger(__name__)

    if context:
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
    else:
        logger.error(f"Error: {str(error)}", exc_info=True)


# Convenience function for backward compatibility
def setup_logging() -> None:
    """Set up logging for the entire application."""
    # This function can be called at application startup
    # to ensure logging is properly configured
    pass
