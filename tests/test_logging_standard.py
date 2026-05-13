"""Tests for logging_standard module."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_logger_state():
    """Reset NexusCoreLogger class state between tests."""
    from nexuscore.logging_standard import NexusCoreLogger

    configured = NexusCoreLogger._configured
    log_dir = NexusCoreLogger._log_dir
    yield
    NexusCoreLogger._configured = configured
    NexusCoreLogger._log_dir = log_dir


class TestGetLogger:
    """get_logger() tests."""

    def test_returns_logger_instance(self):
        from nexuscore.logging_standard import get_logger

        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name_has_nexuscore_prefix(self):
        from nexuscore.logging_standard import get_logger

        logger = get_logger("test.module")
        assert logger.name == "nexuscore.test.module"

    def test_get_logger_same_name_returns_same_logger(self):
        from nexuscore.logging_standard import get_logger

        logger1 = get_logger("same.module")
        logger2 = get_logger("same.module")
        assert logger1 is logger2


class TestNexusCoreLogger:
    """NexusCoreLogger class tests."""

    def test_setup_root_config_sets_level(self):
        from nexuscore.logging_standard import NexusCoreLogger

        NexusCoreLogger._configured = False
        NexusCoreLogger.get_logger("test.setup")
        root = logging.getLogger("nexuscore")
        assert root.level == logging.INFO

    def test_setup_root_config_no_propagate(self):
        from nexuscore.logging_standard import NexusCoreLogger

        NexusCoreLogger._configured = False
        NexusCoreLogger.get_logger("test.propagate")
        root = logging.getLogger("nexuscore")
        assert root.propagate is False

    def test_get_formatter_default(self):
        from nexuscore.logging_standard import NexusCoreLogger

        fmt = NexusCoreLogger._get_formatter()
        assert isinstance(fmt, logging.Formatter)

    def test_get_formatter_verbose(self):
        from nexuscore.logging_standard import NexusCoreLogger

        fmt = NexusCoreLogger._get_formatter(verbose=True)
        assert isinstance(fmt, logging.Formatter)
        assert "%(filename)s" in fmt._fmt

    @patch.dict(os.environ, {"NEXUS_LOG_DIR": "/tmp/test_nexus_logs"})
    def test_get_logs_dir_from_env(self):
        from nexuscore.logging_standard import NexusCoreLogger

        result = NexusCoreLogger._get_logs_dir()
        assert result == Path("/tmp/test_nexus_logs")

    def test_get_logs_dir_default(self):
        from nexuscore.logging_standard import NexusCoreLogger

        with patch.dict(os.environ, {}, clear=True):
            result = NexusCoreLogger._get_logs_dir()
            assert result.name == "logs"

    def test_has_audit_handler_false_when_no_audit(self):
        from nexuscore.logging_standard import NexusCoreLogger

        logger = logging.getLogger("test.no_audit")
        assert NexusCoreLogger._has_audit_handler(logger) is False


class TestAuditLogging:
    """Audit logger functionality tests."""

    def test_get_logger_with_audit(self, tmp_path):
        from nexuscore.logging_standard import NexusCoreLogger

        NexusCoreLogger._configured = False
        NexusCoreLogger._log_dir = tmp_path

        logger = NexusCoreLogger.get_logger("test.audit", audit=True)
        assert NexusCoreLogger._has_audit_handler(logger)

    def test_audit_handler_not_duplicated(self, tmp_path):
        from nexuscore.logging_standard import NexusCoreLogger

        NexusCoreLogger._configured = True
        NexusCoreLogger._log_dir = tmp_path

        logger = NexusCoreLogger.get_logger("test.audit_dup", audit=True)
        handler_count_before = len(logger.handlers)
        logger2 = NexusCoreLogger.get_logger("test.audit_dup", audit=True)
        assert len(logger2.handlers) == handler_count_before
