"""
Tests for core.logger module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging


class TestLogger:
    """Test Logger class"""

    def test_singleton(self):
        from core.logger import Logger
        logger1 = Logger()
        logger2 = Logger()
        assert logger1 is logger2

    def test_logger_setup(self):
        from core.logger import Logger
        logger = Logger()
        assert logger._logger.name == "QingxinTranslator"
        assert logger._logger.level == logging.DEBUG

    def test_log_methods(self):
        from core.logger import Logger
        logger = Logger()

        # Test that methods exist and can be called
        with patch.object(logger._logger, 'debug') as mock_debug:
            logger.debug("test debug")
            mock_debug.assert_called_once_with("test debug")

        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("test info")
            mock_info.assert_called_once_with("test info")

        with patch.object(logger._logger, 'warning') as mock_warning:
            logger.warning("test warning")
            mock_warning.assert_called_once_with("test warning")

        with patch.object(logger._logger, 'error') as mock_error:
            logger.error("test error")
            mock_error.assert_called_once_with("test error")

        with patch.object(logger._logger, 'exception') as mock_exception:
            logger.exception("test exception")
            mock_exception.assert_called_once_with("test exception")

    def test_get_log_file(self):
        from core.logger import Logger, LOG_FILE
        logger = Logger()
        assert logger.get_log_file() == LOG_FILE

    def test_handlers_setup(self):
        from core.logger import Logger
        logger = Logger()
        # Should have at least console and file handlers
        assert len(logger._logger.handlers) >= 2

    def test_global_instance(self):
        from core.logger import log
        assert log is not None
        assert hasattr(log, 'info')
        assert hasattr(log, 'error')