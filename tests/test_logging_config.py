"""
Test suite for logging configuration and utilities.

Tests cover:
- Logger creation and configuration
- Log level management
- File and console output
- Log rotation
- Performance logging
- Error logging with context
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.logging_config import (LoggerManager, LoggingConfig, get_logger, log_error_with_context, log_function_call,
                                log_performance, set_log_level)

class TestLoggingConfig:
    """Test LoggingConfig class functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = LoggingConfig()
        self.config.log_dir = Path(self.temp_dir)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_level_from_env(self) -> None:
        """Test log level extraction from environment variables."""
        with patch.dict(os.environ, {"CONSOLE_LOG_LEVEL": "DEBUG"}):
            config = LoggingConfig()
            assert config.console_level == logging.DEBUG

        with patch.dict(os.environ, {"CONSOLE_LOG_LEVEL": "ERROR"}):
            config = LoggingConfig()
            assert config.console_level == logging.ERROR

    def test_get_formatter_simple(self) -> None:
        """Test simple formatter creation."""
        formatter = self.config.get_formatter("simple")
        assert isinstance(formatter, logging.Formatter)
        assert formatter._fmt is not None and "%(asctime)s" in formatter._fmt

    def test_get_formatter_detailed(self) -> None:
        """Test detailed formatter creation."""
        formatter = self.config.get_formatter("detailed")
        assert isinstance(formatter, logging.Formatter)
        assert formatter._fmt is not None and "%(filename)s" in formatter._fmt

    def test_get_formatter_json(self) -> None:
        """Test JSON formatter creation."""
        formatter = self.config.get_formatter("json")
        assert hasattr(formatter, "format")

    def test_setup_logger(self) -> None:
        """Test logger setup with handlers."""
        logger = self.config.setup_logger("test_logger")

        assert logger.name == "test_logger"
        assert len(logger.handlers) == 2  # Console + File

        # Check console handler
        console_handler = next(
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        )
        assert console_handler.level == self.config.console_level

        # Check file handler
        file_handler = next(
            h
            for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        assert file_handler.level == self.config.file_level


class TestLoggerManager:
    """Test LoggerManager singleton functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        # Reset singleton
        LoggerManager._instance = None
        LoggerManager._loggers = {}

    def teardown_method(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Reset singleton
        LoggerManager._instance = None
        LoggerManager._loggers = {}

    def test_singleton_behavior(self) -> None:
        """Test that LoggerManager is a singleton."""
        manager1 = LoggerManager()
        manager2 = LoggerManager()
        assert manager1 is manager2

    def test_get_logger_creation(self) -> None:
        """Test logger creation and retrieval."""
        manager = LoggerManager()
        logger = manager.get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert "test_module" in manager._loggers

    def test_get_logger_caching(self) -> None:
        """Test that loggers are cached and reused."""
        manager = LoggerManager()
        logger1 = manager.get_logger("test_module")
        logger2 = manager.get_logger("test_module")

        assert logger1 is logger2


class TestLoggingUtilities:
    """Test utility functions for logging."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        # Reset singleton
        LoggerManager._instance = None
        LoggerManager._loggers = {}

    def teardown_method(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Reset singleton
        LoggerManager._instance = None
        LoggerManager._loggers = {}

    def test_get_logger_function(self) -> None:
        """Test get_logger utility function."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_set_log_level(self) -> None:
        """Test set_log_level function."""
        logger = get_logger("test_module")
        set_log_level("ERROR")

        # Check that console handler level was updated
        console_handler = next(
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        )
        assert console_handler.level == logging.ERROR

    def test_log_performance(self, caplog: Any) -> None:
        """Test performance logging function."""
        logger = get_logger("test_module")

        with caplog.at_level(logging.INFO):
            log_performance("test_operation", 1.234, logger)

        assert "Performance: test_operation completed in 1.234s" in caplog.text

    def test_log_error_with_context(self, caplog: Any) -> None:
        """Test error logging with context."""
        logger = get_logger("test_module")
        error = ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            log_error_with_context(error, "test_context", logger)

        assert "Error in test_context: Test error" in caplog.text

    def test_log_function_call(self, caplog: Any) -> None:
        """Test function call logging."""
        logger = get_logger("test_module")

        with caplog.at_level(logging.DEBUG):
            log_function_call("test_function", {"arg1": "value1"}, logger)

        expected = "Calling test_function with args: {'arg1': 'value1'}"
        assert expected in caplog.text


class TestLogRotation:
    """Test log file rotation functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = LoggingConfig()
        self.config.log_dir = Path(self.temp_dir)
        self.config.max_file_size = 100  # Small size for testing

    def teardown_method(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_rotation_setup(self) -> None:
        """Test that log rotation is properly configured."""
        logger = self.config.setup_logger("rotation_test")

        file_handler = next(
            h
            for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        )

        assert file_handler.maxBytes == self.config.max_file_size
        assert file_handler.backupCount == self.config.backup_count


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_environment_variables(self) -> None:
        """Test configuration from environment variables."""
        env_vars = {
            "CONSOLE_LOG_LEVEL": "WARNING",
            "FILE_LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "simple",
            "MAX_LOG_FILE_SIZE": "5242880",  # 5MB
            "LOG_BACKUP_COUNT": "3",
        }

        with patch.dict(os.environ, env_vars):
            config = LoggingConfig()
            config.log_dir = Path(self.temp_dir)

            assert config.console_level == logging.WARNING
            assert config.file_level == logging.DEBUG
            assert config.log_format == "simple"
            assert config.max_file_size == 5242880
            assert config.backup_count == 3


class TestJsonFormatter:
    """Test JSON formatter functionality."""

    def test_json_formatting(self) -> None:
        """Test JSON log record formatting."""
        from src.logging_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "timestamp" in formatted
        assert "level" in formatted
        assert "message" in formatted
        assert "Test message" in formatted


if __name__ == "__main__":
    pytest.main([__file__])
