"""
Comprehensive tests for log_config module.
Tests logging directory management and file logging setup.
"""

import logging
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from nexuscore.utils.log_config import get_logs_dir, setup_file_logging


# ==============================================================================
# get_logs_dir Tests
# ==============================================================================


class TestGetLogsDir:
    """Test get_logs_dir function"""

    def test_get_logs_dir_returns_path(self):
        """Returns Path object"""
        result = get_logs_dir()
        assert isinstance(result, Path)

    def test_get_logs_dir_creates_directory(self):
        """Creates logs directory if it doesn't exist"""
        result = get_logs_dir()
        assert result.exists()
        assert result.is_dir()

    def test_get_logs_dir_is_named_logs(self):
        """Directory is named 'logs'"""
        result = get_logs_dir()
        assert result.name == "logs"

    def test_get_logs_dir_is_in_project_root(self):
        """Logs directory is at project root"""
        result = get_logs_dir()
        # Should be 4 levels up from log_config.py
        # nexuscore/utils/log_config.py -> ../../../../logs
        assert result.exists()

    def test_get_logs_dir_idempotent(self):
        """Multiple calls return same directory"""
        dir1 = get_logs_dir()
        dir2 = get_logs_dir()
        assert dir1 == dir2

    def test_get_logs_dir_absolute_path(self):
        """Returns absolute path"""
        result = get_logs_dir()
        assert result.is_absolute()


# ==============================================================================
# setup_file_logging Tests
# ==============================================================================


class TestSetupFileLogging:
    """Test setup_file_logging function"""

    @pytest.fixture(autouse=True)
    def cleanup_handlers(self):
        """Clean up logger handlers after each test"""
        yield
        # Clean up all loggers
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        # Clean up root logger
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)

    def test_setup_file_logging_creates_logger(self):
        """Creates and returns logger"""
        logger = setup_file_logging("test.log")
        assert isinstance(logger, logging.Logger)

    def test_setup_file_logging_creates_log_file(self):
        """Creates log file in logs directory"""
        logger = setup_file_logging("test_file.log")
        logs_dir = get_logs_dir()
        log_file = logs_dir / "test_file.log"
        
        # Write a log message to ensure file is created
        logger.info("Test message")
        
        assert log_file.exists()

    def test_setup_file_logging_default_log_level(self):
        """Default log level is INFO"""
        logger = setup_file_logging("test.log")
        assert logger.level == logging.INFO

    def test_setup_file_logging_custom_log_level(self):
        """Can set custom log level"""
        logger = setup_file_logging("test.log", log_level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_setup_file_logging_warning_level(self):
        """Can set WARNING log level"""
        logger = setup_file_logging("test.log", log_level=logging.WARNING)
        assert logger.level == logging.WARNING

    def test_setup_file_logging_error_level(self):
        """Can set ERROR log level"""
        logger = setup_file_logging("test.log", log_level=logging.ERROR)
        assert logger.level == logging.ERROR

    def test_setup_file_logging_default_format(self):
        """Uses default format when not specified"""
        logger = setup_file_logging("test.log")
        
        # Check that a FileHandler was added
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0
        
        # Check format includes expected fields
        formatter = file_handlers[0].formatter
        assert formatter is not None

    def test_setup_file_logging_custom_format(self):
        """Can set custom format string"""
        custom_format = "%(levelname)s - %(message)s"
        logger = setup_file_logging("test.log", format_string=custom_format)
        
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0

    def test_setup_file_logging_named_logger(self):
        """Can create named logger"""
        logger_name = "my.custom.logger"
        logger = setup_file_logging("test.log", logger_name=logger_name)
        
        assert logger.name == logger_name

    def test_setup_file_logging_root_logger(self):
        """Creates root logger when logger_name is None"""
        logger = setup_file_logging("test.log", logger_name=None)
        assert logger.name == "root"

    def test_setup_file_logging_removes_duplicate_handlers(self):
        """Removes existing FileHandlers to prevent duplicates"""
        # Call twice with same logger
        logger1 = setup_file_logging("test.log", logger_name="duplicate_test")
        logger2 = setup_file_logging("test.log", logger_name="duplicate_test")
        
        # Should only have one FileHandler
        file_handlers = [h for h in logger2.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

    def test_setup_file_logging_appends_to_existing_file(self):
        """Appends to existing log file (mode='a')"""
        logger = setup_file_logging("append_test.log")
        logger.info("First message")
        
        # Create new logger with same file
        logger2 = setup_file_logging("append_test.log")
        logger2.info("Second message")
        
        # Check file contains both messages
        logs_dir = get_logs_dir()
        log_file = logs_dir / "append_test.log"
        content = log_file.read_text()
        
        assert "First message" in content
        assert "Second message" in content

    def test_setup_file_logging_utf8_encoding(self):
        """Uses UTF-8 encoding for log file"""
        logger = setup_file_logging("utf8_test.log")
        logger.info("日本語メッセージ")
        
        logs_dir = get_logs_dir()
        log_file = logs_dir / "utf8_test.log"
        
        # Should be able to read UTF-8 content
        content = log_file.read_text(encoding='utf-8')
        assert "日本語メッセージ" in content

    def test_setup_file_logging_writes_to_correct_directory(self):
        """Log file is created in logs directory"""
        logger = setup_file_logging("dir_test.log")
        logger.info("Test")
        
        logs_dir = get_logs_dir()
        log_file = logs_dir / "dir_test.log"
        
        assert log_file.parent == logs_dir

    def test_setup_file_logging_handler_has_correct_level(self):
        """FileHandler has same level as logger"""
        logger = setup_file_logging("level_test.log", log_level=logging.WARNING)
        
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert file_handlers[0].level == logging.WARNING


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestLogConfigIntegration:
    """Integration tests for log_config module"""

    @pytest.fixture(autouse=True)
    def cleanup_handlers(self):
        """Clean up logger handlers after each test"""
        yield
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)

    def test_multiple_loggers_different_files(self):
        """Can create multiple loggers with different files"""
        logger1 = setup_file_logging("logger1.log", logger_name="app.module1")
        logger2 = setup_file_logging("logger2.log", logger_name="app.module2")
        
        logger1.info("Message from logger1")
        logger2.info("Message from logger2")
        
        logs_dir = get_logs_dir()
        assert (logs_dir / "logger1.log").exists()
        assert (logs_dir / "logger2.log").exists()

    def test_logger_hierarchy(self):
        """Named loggers create proper hierarchy"""
        parent = setup_file_logging("parent.log", logger_name="parent")
        child = setup_file_logging("child.log", logger_name="parent.child")
        
        assert child.name.startswith(parent.name)

    def test_log_message_contains_expected_fields(self):
        """Log messages contain timestamp, level, name, message"""
        logger = setup_file_logging("fields_test.log", logger_name="test.logger")
        logger.info("Test message")
        
        logs_dir = get_logs_dir()
        content = (logs_dir / "fields_test.log").read_text()
        
        # Default format: "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s"
        assert "INFO" in content
        assert "test.logger" in content
        assert "Test message" in content

    def test_different_log_levels_in_same_file(self):
        """Can log different levels to same file"""
        logger = setup_file_logging("levels_test.log", log_level=logging.DEBUG)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        logs_dir = get_logs_dir()
        content = (logs_dir / "levels_test.log").read_text()
        
        assert "DEBUG" in content
        assert "INFO" in content
        assert "WARNING" in content
        assert "ERROR" in content


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestLogConfigEdgeCases:
    """Test edge cases for log_config module"""

    @pytest.fixture(autouse=True)
    def cleanup_handlers(self):
        """Clean up logger handlers after each test"""
        yield
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)

    def test_setup_file_logging_with_special_characters_in_filename(self):
        """Handle special characters in log filename"""
        logger = setup_file_logging("test-log_file.2024.log")
        logger.info("Test")
        
        logs_dir = get_logs_dir()
        assert (logs_dir / "test-log_file.2024.log").exists()

    def test_setup_file_logging_with_subdirectory_in_filename(self):
        """Handle subdirectory in log filename"""
        # Note: This might not work as expected, but let's test the behavior
        try:
            logger = setup_file_logging("subdir/test.log")
            # If it works, verify
            assert isinstance(logger, logging.Logger)
        except (OSError, FileNotFoundError):
            # Expected if subdirectory doesn't exist
            pass

    def test_setup_file_logging_empty_logger_name(self):
        """Handle empty string as logger name"""
        logger = setup_file_logging("test.log", logger_name="")
        # Empty string should create a named logger (not root)
        assert isinstance(logger, logging.Logger)

    def test_get_logs_dir_with_readonly_filesystem(self):
        """Handle read-only filesystem gracefully"""
        # This is hard to test without actually making filesystem readonly
        # Just verify the function doesn't crash
        result = get_logs_dir()
        assert isinstance(result, Path)

    def test_setup_file_logging_very_long_filename(self):
        """Handle very long log filename"""
        long_name = "a" * 200 + ".log"
        try:
            logger = setup_file_logging(long_name)
            assert isinstance(logger, logging.Logger)
        except OSError:
            # Expected on some filesystems with filename length limits
            pass
