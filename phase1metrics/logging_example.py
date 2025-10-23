"""
Example usage of the logging system.

This module demonstrates how to use the logging configuration
and utilities in your application code.
"""

import time

from .logging_config import (get_logger, log_error_with_context,
                             log_performance, set_log_level)


def example_function() -> None:
    """Example function demonstrating logging usage."""
    # Get a logger for this module
    logger = get_logger(__name__)

    # Different log levels
    logger.debug("This is a debug message - detailed information")
    logger.info("This is an info message - general information")
    logger.warning("This is a warning message - something unexpected happened")
    logger.error("This is an error message - something went wrong")
    logger.critical("This is a critical message - serious error")

    # Performance logging
    start_time = time.time()
    time.sleep(0.1)  # Simulate work
    log_performance("example_function", time.time() - start_time, logger)

    # Error logging with context
    try:
        raise ValueError("Example error for demonstration")
    except Exception as e:
        log_error_with_context(e, "example_function", logger)


def example_with_correlation_id() -> None:
    """Example using correlation ID for request tracing."""
    # Get logger with correlation ID
    correlation_id = "req_12345"
    logger = get_logger(__name__, correlation_id)

    logger.info("Processing request with correlation ID")
    logger.debug("Request details: user_id=123, action=update")

    # All subsequent log messages will include the correlation ID


def example_environment_configuration() -> None:
    """Example showing environment variable configuration."""
    import os

    # Set environment variables for different configurations
    os.environ["CONSOLE_LOG_LEVEL"] = "INFO"
    os.environ["FILE_LOG_LEVEL"] = "DEBUG"
    os.environ["LOG_FORMAT"] = "detailed"

    # Or change log level programmatically
    set_log_level("DEBUG")

    logger = get_logger(__name__)
    logger.debug("This will now be visible in console")
    logger.info("This will be visible in both console and file")


if __name__ == "__main__":
    print("=== Basic Logging Example ===")
    example_function()

    print("\n=== Correlation ID Example ===")
    example_with_correlation_id()

    print("\n=== Environment Configuration Example ===")
    example_environment_configuration()

    print("\n=== Log Files Created ===")
    from pathlib import Path
    log_dir = Path("logs")
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            print(f"  - {log_file}")
