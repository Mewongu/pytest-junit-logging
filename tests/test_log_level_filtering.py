"""
Tests for log level filtering functionality.
"""

import pytest
import logging
import sys
import tempfile
import subprocess
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

from pytest_junit_logging.plugin import pytest_addoption, pytest_configure
from pytest_junit_logging.log_capture import install_log_capture, get_log_capture


class TestCommandLineOption:
    """Test --junit-log-level command line option."""
    
    def test_pytest_addoption_registration(self):
        """Test that the command line option is properly registered."""
        # Mock parser and group
        mock_group = MagicMock()
        mock_parser = MagicMock()
        mock_parser.getgroup.return_value = mock_group
        
        pytest_addoption(mock_parser)
        
        # Verify option was added
        mock_parser.getgroup.assert_called_once_with("junit-logging", "JUnit XML log integration")
        mock_group.addoption.assert_called_once_with(
            "--junit-log-level",
            action="store",
            default="DEBUG",
            choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
            help="Minimum log level to include in JUnit XML (default: DEBUG)"
        )
    
    def test_pytest_configure_with_log_level(self):
        """Test pytest_configure handles log level option."""
        config = MagicMock()
        config.option.xmlpath = "/tmp/results.xml"
        config.option.junit_log_level = "WARNING"
        
        with patch('pytest_junit_logging.plugin.install_log_capture') as mock_install:
            pytest_configure(config)
            
            # Should call install with WARNING level (30)
            mock_install.assert_called_once_with(logging.WARNING)
    
    def test_pytest_configure_without_junit_xml(self):
        """Test pytest_configure skips installation without junit-xml."""
        config = MagicMock()
        config.option.xmlpath = None
        config.option.junit_log_level = "ERROR"
        
        with patch('pytest_junit_logging.plugin.install_log_capture') as mock_install:
            pytest_configure(config)
            
            # Should not install handler
            mock_install.assert_not_called()
    
    def test_pytest_configure_default_log_level(self):
        """Test pytest_configure uses DEBUG as default log level."""
        config = MagicMock()
        config.option.xmlpath = "/tmp/results.xml"
        # No junit_log_level attribute
        del config.option.junit_log_level
        
        with patch('pytest_junit_logging.plugin.install_log_capture') as mock_install:
            pytest_configure(config)
            
            # Should call with DEBUG level
            mock_install.assert_called_once_with(logging.DEBUG)


class TestLogLevelFiltering:
    """Test log level filtering in log capture."""
    
    def test_install_log_capture_with_custom_level(self):
        """Test install_log_capture respects custom log level."""
        with patch('pytest_junit_logging.log_capture.logging.getLogger') as mock_get_logger, \
             patch('pytest_junit_logging.log_capture.get_log_capture') as mock_get_capture:
            
            mock_root_logger = MagicMock()
            mock_root_logger.level = logging.ERROR  # Higher than WARNING
            mock_root_logger.handlers = []
            mock_get_logger.return_value = mock_root_logger
            
            mock_capture = MagicMock()
            mock_get_capture.return_value = mock_capture
            
            install_log_capture(logging.WARNING)
            
            # Should add handler and set WARNING level
            mock_root_logger.addHandler.assert_called_once_with(mock_capture)
            mock_capture.setLevel.assert_called_once_with(logging.WARNING)
            
            # Should lower root logger level to WARNING
            mock_root_logger.setLevel.assert_called_once_with(logging.WARNING)
    
    def test_install_log_capture_preserves_lower_root_level(self):
        """Test install_log_capture doesn't raise root logger level."""
        with patch('pytest_junit_logging.log_capture.logging.getLogger') as mock_get_logger:
            mock_root_logger = MagicMock()
            mock_root_logger.level = logging.DEBUG  # Lower than WARNING
            mock_root_logger.handlers = []
            mock_get_logger.return_value = mock_root_logger
            
            install_log_capture(logging.WARNING)
            
            # Should not change root logger level
            mock_root_logger.setLevel.assert_not_called()
    
    def test_handler_filters_logs_by_level(self, log_capture):
        """Test that handler filters logs based on its level."""
        # Set handler to WARNING level
        log_capture.setLevel(logging.WARNING)
        log_capture.set_current_test_item("test.example.test_method")
        
        # Create log records at different levels
        debug_record = logging.LogRecord(
            name="test.logger", level=logging.DEBUG, pathname="/test.py", 
            lineno=10, msg="Debug message", args=(), exc_info=None
        )
        debug_record.created = 1234567890.123
        
        warning_record = logging.LogRecord(
            name="test.logger", level=logging.WARNING, pathname="/test.py",
            lineno=20, msg="Warning message", args=(), exc_info=None
        )
        warning_record.created = 1234567890.124
        
        error_record = logging.LogRecord(
            name="test.logger", level=logging.ERROR, pathname="/test.py",
            lineno=30, msg="Error message", args=(), exc_info=None
        )
        error_record.created = 1234567890.125
        
        with patch('pytest_junit_logging.log_capture.datetime') as mock_datetime:
            mock_datetime.fromtimestamp.return_value.isoformat.return_value = "2025-11-27T10:00:00.000000+00:00"
            
            # Emit records - DEBUG should be filtered out
            log_capture.emit(debug_record)  # Should be filtered
            log_capture.emit(warning_record)  # Should be captured
            log_capture.emit(error_record)  # Should be captured
        
        # Should only have WARNING and ERROR logs
        assert len(log_capture.logs) == 2
        assert log_capture.logs[0].level == "WARNING"
        assert log_capture.logs[0].message == "Warning message"
        assert log_capture.logs[1].level == "ERROR"
        assert log_capture.logs[1].message == "Error message"


class TestEndToEndLogLevelFiltering:
    """Test log level filtering in end-to-end scenarios."""
    
    def test_warning_level_filtering(self, temp_dir):
        """Test that only WARNING+ logs are captured when specified."""
        test_project = temp_dir / "test_project"
        test_project.mkdir()
        
        test_content = dedent("""
            import logging
            
            def test_with_various_log_levels():
                logging.debug("This debug message should be filtered out")
                logging.info("This info message should be filtered out") 
                logging.warning("This warning message should appear")
                logging.error("This error message should appear")
                assert True
        """)
        (test_project / "test_levels.py").write_text(test_content)
        
        # Run pytest with WARNING log level
        xml_file = test_project / "results.xml"
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(test_project),
            f"--junit-xml={xml_file}",
            "--junit-log-level=WARNING",
            "-v"
        ], capture_output=True, text=True, cwd=str(test_project))
        
        assert result.returncode == 0
        assert xml_file.exists()
        
        # Parse XML and check logs
        tree = ET.parse(xml_file)
        testcase = tree.find(".//testcase")
        logs_element = testcase.find("logs")
        assert logs_element is not None
        
        log_messages = [log.text for log in logs_element.findall("log")]
        log_levels = [log.get("level") for log in logs_element.findall("log")]
        
        # Should only have WARNING and ERROR
        assert "This warning message should appear" in log_messages
        assert "This error message should appear" in log_messages
        assert "This debug message should be filtered out" not in log_messages
        assert "This info message should be filtered out" not in log_messages
        
        # Verify log levels
        assert "DEBUG" not in log_levels
        assert "INFO" not in log_levels
        assert "WARNING" in log_levels
        assert "ERROR" in log_levels
    
    def test_error_level_filtering(self, temp_dir):
        """Test that only ERROR+ logs are captured when specified."""
        test_project = temp_dir / "test_project"
        test_project.mkdir()
        
        test_content = dedent("""
            import logging
            
            def test_with_error_level_only():
                logging.warning("This warning should be filtered out")
                logging.error("This error should appear")
                logging.critical("This critical should appear")
                assert True
        """)
        (test_project / "test_errors.py").write_text(test_content)
        
        xml_file = test_project / "results.xml"
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(test_project), 
            f"--junit-xml={xml_file}",
            "--junit-log-level=ERROR",
            "-v"
        ], capture_output=True, text=True, cwd=str(test_project))
        
        assert result.returncode == 0
        assert xml_file.exists()
        
        tree = ET.parse(xml_file)
        testcase = tree.find(".//testcase")
        logs_element = testcase.find("logs")
        assert logs_element is not None
        
        log_messages = [log.text for log in logs_element.findall("log")]
        log_levels = [log.get("level") for log in logs_element.findall("log")]
        
        # Should only have ERROR and CRITICAL
        assert "This error should appear" in log_messages
        assert "This critical should appear" in log_messages
        assert "This warning should be filtered out" not in log_messages
        
        assert "WARNING" not in log_levels
        assert "ERROR" in log_levels
        assert "CRITICAL" in log_levels
    
    def test_debug_level_captures_all(self, temp_dir):
        """Test that DEBUG level captures all logs (default behavior)."""
        test_project = temp_dir / "test_project"
        test_project.mkdir()
        
        test_content = dedent("""
            import logging
            
            def test_with_all_levels():
                logging.debug("Debug message")
                logging.info("Info message") 
                logging.warning("Warning message")
                logging.error("Error message")
                assert True
        """)
        (test_project / "test_all.py").write_text(test_content)
        
        xml_file = test_project / "results.xml"
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(test_project),
            f"--junit-xml={xml_file}",
            "--junit-log-level=DEBUG",
            "-v"
        ], capture_output=True, text=True, cwd=str(test_project))
        
        assert result.returncode == 0
        assert xml_file.exists()
        
        tree = ET.parse(xml_file)
        testcase = tree.find(".//testcase")
        logs_element = testcase.find("logs")
        assert logs_element is not None
        
        log_messages = [log.text for log in logs_element.findall("log")]
        log_levels = [log.get("level") for log in logs_element.findall("log")]
        
        # Should have all levels
        assert "Debug message" in log_messages
        assert "Info message" in log_messages
        assert "Warning message" in log_messages
        assert "Error message" in log_messages
        
        assert "DEBUG" in log_levels
        assert "INFO" in log_levels
        assert "WARNING" in log_levels
        assert "ERROR" in log_levels
    
    def test_assertion_logs_always_included(self, temp_dir):
        """Test that ASSERT level logs are always included regardless of filter."""
        test_project = temp_dir / "test_project"
        test_project.mkdir()
        
        test_content = dedent("""
            import logging
            
            def test_with_assertion_failure():
                logging.debug("Debug before assertion")
                assert 1 == 2, "Custom assertion message"
        """)
        (test_project / "test_assertion.py").write_text(test_content)
        
        xml_file = test_project / "results.xml"
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(test_project),
            f"--junit-xml={xml_file}",
            "--junit-log-level=ERROR",  # Should filter out DEBUG but keep ASSERT
            "-v"
        ], capture_output=True, text=True, cwd=str(test_project))
        
        # Test should fail but XML should be generated
        assert result.returncode != 0
        assert xml_file.exists()
        
        tree = ET.parse(xml_file)
        testcase = tree.find(".//testcase")
        logs_element = testcase.find("logs")
        assert logs_element is not None
        
        log_levels = [log.get("level") for log in logs_element.findall("log")]
        log_messages = [log.text for log in logs_element.findall("log")]
        
        # DEBUG should be filtered out, but ASSERT should be present
        assert "DEBUG" not in log_levels
        assert "ASSERT" in log_levels
        assert "Debug before assertion" not in log_messages
        assert any("Custom assertion message" in msg for msg in log_messages)