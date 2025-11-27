"""
Tests for XML formatting functionality.
"""

import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

from pytest_junit_logging.log_capture import LogEntry
from pytest_junit_logging.xml_formatter import (
    _get_relative_path,
    add_logs_to_testcase,
    format_log_entry_for_xml,
    get_testcase_id_from_element,
)


class TestLogEntryXMLFormatting:
    """Test converting log entries to XML elements."""

    def test_basic_log_entry_formatting(self, sample_log_entry):
        """Test basic log entry to XML conversion."""
        with patch("pytest_junit_logging.xml_formatter._get_relative_path") as mock_rel_path:
            mock_rel_path.return_value = "tests/test_example.py"

            xml_element = format_log_entry_for_xml(sample_log_entry)

            assert xml_element.tag == "log"
            assert xml_element.get("step") == "test"
            assert xml_element.get("ts") == "2025-11-27T10:00:00.000000+00:00"
            assert xml_element.get("level") == "INFO"
            assert xml_element.get("src") == "tests/test_example.py:42"
            assert xml_element.text == "Test log message"

    def test_html_escaping_in_log_message(self):
        """Test that HTML entities are properly escaped in log messages."""
        log_entry = LogEntry(
            timestamp="2025-11-27T10:00:00.000000+00:00",
            level="ERROR",
            message="Error: <value> should be > 5 & < 10",
            filename="/workspace/test.py",
            lineno=25,
            test_item_id="test.example.test_method",
        )

        with patch("pytest_junit_logging.xml_formatter._get_relative_path") as mock_rel_path:
            mock_rel_path.return_value = "test.py"

            xml_element = format_log_entry_for_xml(log_entry)

            # Should escape HTML entities
            assert xml_element.text == "Error: &lt;value&gt; should be &gt; 5 &amp; &lt; 10"

    def test_special_characters_in_filename(self):
        """Test handling of special characters in filenames."""
        log_entry = LogEntry(
            timestamp="2025-11-27T10:00:00.000000+00:00",
            level="DEBUG",
            message="Debug message",
            filename="/workspace/tests with spaces/test-file.py",
            lineno=10,
            test_item_id="test.example.test_method",
        )

        with patch("pytest_junit_logging.xml_formatter._get_relative_path") as mock_rel_path:
            mock_rel_path.return_value = "tests with spaces/test-file.py"

            xml_element = format_log_entry_for_xml(log_entry)

            assert xml_element.get("src") == "tests with spaces/test-file.py:10"

    def test_step_attribute_variations(self):
        """Test that step attribute is set correctly based on fixture phase."""
        # Test setup phase
        setup_log = LogEntry(
            timestamp="2025-11-27T10:00:00.000000+00:00",
            level="INFO",
            message="Setup message",
            filename="/workspace/test.py",
            lineno=10,
            test_item_id="test.example.test_method",
            fixture_phase="setup",
        )

        # Test teardown phase
        teardown_log = LogEntry(
            timestamp="2025-11-27T10:00:01.000000+00:00",
            level="INFO",
            message="Teardown message",
            filename="/workspace/test.py",
            lineno=20,
            test_item_id="test.example.test_method",
            fixture_phase="teardown",
        )

        # Test execution phase (no fixture_phase)
        test_log = LogEntry(
            timestamp="2025-11-27T10:00:00.500000+00:00",
            level="DEBUG",
            message="Test execution message",
            filename="/workspace/test.py",
            lineno=15,
            test_item_id="test.example.test_method",
        )

        with patch("pytest_junit_logging.xml_formatter._get_relative_path") as mock_rel_path:
            mock_rel_path.return_value = "test.py"

            setup_xml = format_log_entry_for_xml(setup_log)
            teardown_xml = format_log_entry_for_xml(teardown_log)
            test_xml = format_log_entry_for_xml(test_log)

            assert setup_xml.get("step") == "setup"
            assert teardown_xml.get("step") == "teardown"
            assert test_xml.get("step") == "test"


class TestRelativePathGeneration:
    """Test relative path generation functionality."""

    def test_relative_path_within_project(self, temp_dir):
        """Test relative path generation for files within project."""
        # Create a test file in temp directory
        test_file = temp_dir / "subdir" / "test_file.py"
        test_file.parent.mkdir(parents=True)
        test_file.touch()

        # Mock os.getcwd to return our temp directory
        with patch("pytest_junit_logging.xml_formatter.os.getcwd") as mock_cwd:
            mock_cwd.return_value = str(temp_dir)

            relative_path = _get_relative_path(str(test_file))
            assert relative_path == "subdir/test_file.py"

    def test_relative_path_outside_project(self, temp_dir):
        """Test relative path generation for files outside project."""
        # Use a file outside our temp directory
        outside_file = "/some/other/path/file.py"

        with patch("pytest_junit_logging.xml_formatter.os.getcwd") as mock_cwd:
            mock_cwd.return_value = str(temp_dir)

            relative_path = _get_relative_path(outside_file)
            # Should fallback to basename for files outside project
            assert relative_path == "file.py"

    def test_relative_path_error_handling(self):
        """Test error handling in relative path generation."""
        # Test with invalid path that might cause os.path operations to fail
        with patch("pytest_junit_logging.xml_formatter.os.getcwd") as mock_cwd:
            with patch("pytest_junit_logging.xml_formatter.os.path.relpath") as mock_relpath:
                mock_cwd.return_value = "/workspace"
                mock_relpath.side_effect = ValueError("Invalid path")

                relative_path = _get_relative_path("/some/path/file.py")
                # Should fallback to basename on error
                assert relative_path == "file.py"


class TestTestcaseXMLModification:
    """Test modification of testcase XML elements."""

    def test_add_logs_to_testcase_with_logs(self):
        """Test adding logs to a testcase element when logs exist."""
        # Create a testcase element
        testcase = ET.Element("testcase")
        testcase.set("classname", "tests.test_example.TestClass")
        testcase.set("name", "test_method")

        # Mock logs to be returned
        mock_logs = [
            LogEntry(
                timestamp="2025-11-27T10:00:00.000000+00:00",
                level="INFO",
                message="Test log 1",
                filename="/workspace/test.py",
                lineno=10,
                test_item_id="tests.test_example.TestClass.test_method",
            ),
            LogEntry(
                timestamp="2025-11-27T10:00:01.000000+00:00",
                level="DEBUG",
                message="Test log 2",
                filename="/workspace/test.py",
                lineno=15,
                test_item_id="tests.test_example.TestClass.test_method",
            ),
        ]

        with patch("pytest_junit_logging.xml_formatter.get_test_tracker") as mock_get_tracker:
            with patch("pytest_junit_logging.xml_formatter._get_relative_path") as mock_rel_path:
                mock_tracker = MagicMock()
                mock_tracker.associate_logs_with_test.return_value = mock_logs
                mock_get_tracker.return_value = mock_tracker
                mock_rel_path.return_value = "test.py"

                add_logs_to_testcase(testcase, "tests.test_example.TestClass.test_method")

                # Should have added logs element
                logs_element = testcase.find("logs")
                assert logs_element is not None

                # Should have two log sub-elements
                log_elements = logs_element.findall("log")
                assert len(log_elements) == 2

                # Verify first log
                assert log_elements[0].get("level") == "INFO"
                assert log_elements[0].text == "Test log 1"

                # Verify second log
                assert log_elements[1].get("level") == "DEBUG"
                assert log_elements[1].text == "Test log 2"

    def test_add_logs_to_testcase_with_no_logs(self):
        """Test adding logs to a testcase element when no logs exist."""
        testcase = ET.Element("testcase")
        testcase.set("classname", "tests.test_example.TestClass")
        testcase.set("name", "test_method")

        with patch("pytest_junit_logging.xml_formatter.get_test_tracker") as mock_get_tracker:
            mock_tracker = MagicMock()
            mock_tracker.associate_logs_with_test.return_value = []  # No logs
            mock_get_tracker.return_value = mock_tracker

            add_logs_to_testcase(testcase, "tests.test_example.TestClass.test_method")

            # Should not have added logs element
            logs_element = testcase.find("logs")
            assert logs_element is None


class TestTestcaseIdExtraction:
    """Test extracting test IDs from testcase XML elements."""

    def test_extract_testcase_id_with_class(self):
        """Test extracting test ID from testcase with class."""
        testcase = ET.Element("testcase")
        testcase.set("classname", "tests.test_example.TestClass")
        testcase.set("name", "test_method")

        test_id = get_testcase_id_from_element(testcase)
        assert test_id == "tests.test_example.TestClass.test_method"

    def test_extract_testcase_id_without_class(self):
        """Test extracting test ID from testcase without class."""
        testcase = ET.Element("testcase")
        testcase.set("classname", "tests.test_example")
        testcase.set("name", "test_function")

        test_id = get_testcase_id_from_element(testcase)
        assert test_id == "tests.test_example.test_function"

    def test_extract_testcase_id_parametrized(self):
        """Test extracting test ID from parametrized test."""
        testcase = ET.Element("testcase")
        testcase.set("classname", "tests.test_example.TestClass")
        testcase.set("name", "test_method[param-value]")

        test_id = get_testcase_id_from_element(testcase)
        assert test_id == "tests.test_example.TestClass.test_method[param-value]"

    def test_extract_testcase_id_missing_attributes(self):
        """Test extracting test ID when attributes are missing."""
        testcase = ET.Element("testcase")
        testcase.set("name", "test_method")
        # No classname attribute

        test_id = get_testcase_id_from_element(testcase)
        assert test_id == "test_method"

        # Test with no name either
        testcase_empty = ET.Element("testcase")
        test_id_empty = get_testcase_id_from_element(testcase_empty)
        assert test_id_empty == ""


class TestXMLTreeManipulation:
    """Test complete XML tree manipulation scenarios."""

    def test_full_xml_modification_workflow(self, temp_dir):
        """Test the complete workflow of modifying XML with logs."""
        # Create sample XML content
        xml_content = """<?xml version='1.0' encoding='utf-8'?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="1" time="0.01">
        <testcase classname="tests.test_example.TestClass" name="test_method" time="0.001" />
    </testsuite>
</testsuites>"""

        # Write XML to temporary file
        xml_file = temp_dir / "test_results.xml"
        xml_file.write_text(xml_content)

        # Parse the XML
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Mock logs to add
        mock_logs = [
            LogEntry(
                timestamp="2025-11-27T10:00:00.000000+00:00",
                level="INFO",
                message="Test execution started",
                filename="/workspace/test_example.py",
                lineno=5,
                test_item_id="tests.test_example.TestClass.test_method",
            )
        ]

        # Find testcase and add logs
        testcase = root.find(".//testcase")

        with patch("pytest_junit_logging.xml_formatter.get_test_tracker") as mock_get_tracker:
            with patch("pytest_junit_logging.xml_formatter._get_relative_path") as mock_rel_path:
                mock_tracker = MagicMock()
                mock_tracker.associate_logs_with_test.return_value = mock_logs
                mock_get_tracker.return_value = mock_tracker
                mock_rel_path.return_value = "test_example.py"

                test_id = get_testcase_id_from_element(testcase)
                add_logs_to_testcase(testcase, test_id)

        # Verify logs were added
        logs_element = testcase.find("logs")
        assert logs_element is not None

        log_element = logs_element.find("log")
        assert log_element is not None
        assert log_element.get("level") == "INFO"
        assert log_element.get("src") == "test_example.py:5"
        assert log_element.text == "Test execution started"
