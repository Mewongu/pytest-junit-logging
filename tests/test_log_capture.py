"""
Unit tests for log capture functionality.
"""

import logging
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from pytest_junit_logging.log_capture import (
    TestLogCapture, LogEntry, TestItemTracker, 
    get_log_capture, get_test_tracker,
    install_log_capture, uninstall_log_capture
)


class TestLogEntry:
    """Test LogEntry dataclass functionality."""
    
    def test_log_entry_creation(self, sample_log_entry):
        """Test basic log entry creation."""
        assert sample_log_entry.timestamp == "2025-11-27T10:00:00.000000+00:00"
        assert sample_log_entry.level == "INFO"
        assert sample_log_entry.message == "Test log message"
        assert sample_log_entry.filename == "/workspace/tests/test_example.py"
        assert sample_log_entry.lineno == 42
        assert sample_log_entry.test_item_id == "tests.test_example.TestClass.test_method"

    def test_log_entry_with_fixture_info(self):
        """Test log entry with fixture scope information."""
        entry = LogEntry(
            timestamp="2025-11-27T10:00:00.000000+00:00",
            level="DEBUG",
            message="Fixture setup",
            filename="/workspace/conftest.py",
            lineno=10,
            test_item_id="tests.test_example.TestClass.test_method",
            fixture_scope="session",
            fixture_phase="setup"
        )
        assert entry.fixture_scope == "session"
        assert entry.fixture_phase == "setup"


class TestTestLogCapture:
    """Test TestLogCapture logging handler."""
    
    def test_handler_initialization(self, log_capture):
        """Test handler initialization."""
        assert log_capture.logs == []
        assert log_capture.current_test_item is None
        assert log_capture.current_fixture_context is None
    
    def test_set_current_test_item(self, log_capture):
        """Test setting current test item."""
        test_id = "test.example.test_method"
        log_capture.set_current_test_item(test_id)
        assert log_capture.current_test_item == test_id
    
    def test_set_fixture_context(self, log_capture):
        """Test setting fixture context."""
        context = {
            "name": "test_fixture",
            "scope": "function",
            "phase": "setup"
        }
        log_capture.set_fixture_context(context)
        assert log_capture.current_fixture_context == context
    
    @patch('pytest_junit_logging.log_capture.datetime')
    def test_emit_basic_log(self, mock_datetime, log_capture):
        """Test basic log emission."""
        # Mock datetime
        mock_datetime.fromtimestamp.return_value.isoformat.return_value = "2025-11-27T10:00:00.000000+00:00"
        
        # Set test context
        log_capture.set_current_test_item("test.example.test_method")
        
        # Create log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/workspace/test_file.py",
            lineno=25,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.created = 1234567890.123
        
        # Emit log
        log_capture.emit(record)
        
        # Verify log was captured
        assert len(log_capture.logs) == 1
        log_entry = log_capture.logs[0]
        assert log_entry.level == "INFO"
        assert log_entry.message == "Test message"
        assert log_entry.filename == "/workspace/test_file.py"
        assert log_entry.lineno == 25
        assert log_entry.test_item_id == "test.example.test_method"

    @patch('pytest_junit_logging.log_capture.datetime')
    def test_emit_with_fixture_context(self, mock_datetime, log_capture):
        """Test log emission with fixture context."""
        mock_datetime.fromtimestamp.return_value.isoformat.return_value = "2025-11-27T10:00:00.000000+00:00"
        
        # Set fixture context
        fixture_context = {
            "name": "session_fixture", 
            "scope": "session",
            "phase": "setup",
            "test_item_id": "test.example.test_method"
        }
        log_capture.set_fixture_context(fixture_context)
        
        # Create and emit log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="/workspace/conftest.py",
            lineno=15,
            msg="Session fixture initializing",
            args=(),
            exc_info=None
        )
        record.created = 1234567890.123
        
        log_capture.emit(record)
        
        # Verify log captured with fixture info
        assert len(log_capture.logs) == 1
        log_entry = log_capture.logs[0]
        assert log_entry.fixture_scope == "session"
        assert log_entry.fixture_phase == "setup"
        assert log_entry.test_item_id == "test.example.test_method"
    
    def test_get_logs_for_test(self, log_capture, sample_log_entry):
        """Test getting logs for specific test."""
        # Add logs for different tests
        log_capture.logs = [
            sample_log_entry,
            LogEntry(
                timestamp="2025-11-27T10:01:00.000000+00:00",
                level="DEBUG",
                message="Different test log",
                filename="/workspace/other_test.py",
                lineno=10,
                test_item_id="tests.other.test_method"
            )
        ]
        
        # Get logs for specific test
        test_logs = log_capture.get_logs_for_test("tests.test_example.TestClass.test_method")
        assert len(test_logs) == 1
        assert test_logs[0] == sample_log_entry
    
    def test_clear_logs(self, log_capture, sample_log_entry):
        """Test clearing captured logs."""
        log_capture.logs = [sample_log_entry]
        assert len(log_capture.logs) == 1
        
        log_capture.clear_logs()
        assert len(log_capture.logs) == 0


class TestTestItemTracker:
    """Test TestItemTracker functionality."""
    
    def test_tracker_initialization(self, test_tracker):
        """Test tracker initialization."""
        assert test_tracker.current_test_item is None
        assert test_tracker.current_fixture_context is None
        assert test_tracker.session_logs == []
        assert test_tracker.module_logs == {}
        assert test_tracker.test_logs == {}
    
    def test_get_test_item_id_class_method(self, test_tracker, mock_test_item):
        """Test getting test item ID from class method."""
        test_id = test_tracker.get_test_item_id(mock_test_item)
        assert test_id == "tests.test_example.TestClass.test_method"
    
    def test_get_test_item_id_parametrized(self, test_tracker, mock_parametrized_item):
        """Test getting test item ID from parametrized test."""
        test_id = test_tracker.get_test_item_id(mock_parametrized_item)
        assert test_id == "tests.test_example.TestClass.test_method[param1]"
    
    def test_get_module_id(self, test_tracker, mock_test_item):
        """Test getting module ID from test item."""
        module_id = test_tracker.get_module_id(mock_test_item)
        assert module_id == "test_example"
    
    @patch('pytest_junit_logging.log_capture.get_log_capture')
    def test_set_current_test_item(self, mock_get_capture, test_tracker, mock_test_item):
        """Test setting current test item."""
        mock_capture = MagicMock()
        mock_get_capture.return_value = mock_capture
        
        test_tracker.set_current_test_item(mock_test_item)
        
        assert test_tracker.current_test_item == "tests.test_example.TestClass.test_method"
        mock_capture.set_current_test_item.assert_called_once_with("tests.test_example.TestClass.test_method")
    
    def test_generate_test_id_from_node(self, test_tracker):
        """Test generating test ID from pytest node."""
        mock_node = MagicMock()
        mock_node.nodeid = "tests/test_module.py::TestClass::test_method[param]"
        
        test_id = test_tracker._generate_test_id_from_node(mock_node)
        assert test_id == "tests.test_module.TestClass.test_method[param]"
    
    def test_set_fixture_context(self, test_tracker, mock_fixturedef, mock_request):
        """Test setting fixture context."""
        with patch.object(test_tracker, '_generate_test_id_from_node') as mock_gen_id:
            mock_gen_id.return_value = "tests.test_example.TestClass.test_method"
            
            test_tracker.set_fixture_context(mock_fixturedef, mock_request, "setup")
            
            assert test_tracker.current_fixture_context["name"] == "test_fixture"
            assert test_tracker.current_fixture_context["scope"] == "function"
            assert test_tracker.current_fixture_context["phase"] == "setup"
            assert test_tracker.current_fixture_context["test_item_id"] == "tests.test_example.TestClass.test_method"


class TestGlobalFunctions:
    """Test global log capture functions."""
    
    def test_get_log_capture_singleton(self):
        """Test that get_log_capture returns singleton."""
        capture1 = get_log_capture()
        capture2 = get_log_capture()
        assert capture1 is capture2
    
    def test_get_test_tracker_singleton(self):
        """Test that get_test_tracker returns singleton."""
        tracker1 = get_test_tracker()
        tracker2 = get_test_tracker()
        assert tracker1 is tracker2
    
    @patch('pytest_junit_logging.log_capture.logging.getLogger')
    def test_install_log_capture(self, mock_get_logger):
        """Test installing log capture handler."""
        mock_root_logger = MagicMock()
        mock_root_logger.level = logging.WARNING  # Higher than DEBUG
        mock_root_logger.handlers = []  # No handlers initially
        mock_get_logger.return_value = mock_root_logger
        
        install_log_capture()
        
        # Should add handler to root logger
        mock_root_logger.addHandler.assert_called_once()
        mock_root_logger.setLevel.assert_called_once_with(logging.DEBUG)
    
    @patch('pytest_junit_logging.log_capture.logging.getLogger')
    def test_uninstall_log_capture(self, mock_get_logger):
        """Test uninstalling log capture handler."""
        mock_root_logger = MagicMock()
        mock_capture = MagicMock()
        mock_get_logger.return_value = mock_root_logger
        mock_root_logger.handlers = [mock_capture]
        
        with patch('pytest_junit_logging.log_capture.get_log_capture') as mock_get_capture:
            mock_get_capture.return_value = mock_capture
            
            uninstall_log_capture()
            
            mock_root_logger.removeHandler.assert_called_once_with(mock_capture)