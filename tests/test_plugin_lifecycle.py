"""
Tests for plugin lifecycle and hook integration.
"""

import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, call, patch

import pytest

from pytest_junit_logging.plugin import (
    pytest_configure,
    pytest_fixture_post_finalizer,
    pytest_fixture_setup,
    pytest_runtest_call,
    pytest_runtest_makereport,
    pytest_runtest_setup,
    pytest_runtest_teardown,
    pytest_sessionfinish,
)


class TestPluginConfiguration:
    """Test plugin configuration and activation."""

    def test_pytest_configure_with_junit_xml(self):
        """Test that plugin activates when junit-xml is specified."""
        config = MagicMock()
        config.option.xmlpath = "/tmp/results.xml"
        config.option.junit_log_level = "DEBUG"

        with patch("pytest_junit_logging.plugin.install_log_capture") as mock_install:
            pytest_configure(config)
            mock_install.assert_called_once()

    def test_pytest_configure_without_junit_xml(self):
        """Test that plugin doesn't activate without junit-xml."""
        config = MagicMock()
        config.option.xmlpath = None

        with patch("pytest_junit_logging.plugin.install_log_capture") as mock_install:
            pytest_configure(config)
            mock_install.assert_not_called()


class TestTestItemHooks:
    """Test test item lifecycle hooks."""

    def test_pytest_runtest_setup(self, mock_test_item):
        """Test runtest setup hook."""
        with patch("pytest_junit_logging.plugin.get_test_tracker") as mock_get_tracker:
            mock_tracker = MagicMock()
            mock_get_tracker.return_value = mock_tracker

            pytest_runtest_setup(mock_test_item)

            mock_tracker.set_current_test_item.assert_called_once_with(mock_test_item)

    def test_pytest_runtest_call(self, mock_test_item):
        """Test runtest call hook."""
        # The call hook currently doesn't do anything - just verify it doesn't error
        pytest_runtest_call(mock_test_item)

    def test_pytest_runtest_teardown(self, mock_test_item):
        """Test runtest teardown hook."""
        # The teardown hook currently doesn't do anything - just verify it doesn't error
        mock_nextitem = MagicMock()
        pytest_runtest_teardown(mock_test_item, mock_nextitem)


class TestFixtureHooks:
    """Test fixture lifecycle hooks."""

    def test_pytest_fixture_setup(self, mock_fixturedef, mock_request):
        """Test fixture setup hook."""
        with patch("pytest_junit_logging.plugin.get_test_tracker") as mock_get_tracker:
            mock_tracker = MagicMock()
            mock_get_tracker.return_value = mock_tracker

            pytest_fixture_setup(mock_fixturedef, mock_request)

            mock_tracker.set_fixture_context.assert_called_once_with(
                mock_fixturedef, mock_request, "setup"
            )

    def test_pytest_fixture_post_finalizer(self, mock_fixturedef, mock_request):
        """Test fixture teardown hook."""
        with patch("pytest_junit_logging.plugin.get_test_tracker") as mock_get_tracker:
            mock_tracker = MagicMock()
            mock_get_tracker.return_value = mock_tracker

            pytest_fixture_post_finalizer(mock_fixturedef, mock_request)

            # Should be called twice: once for teardown, once to clear
            assert mock_tracker.set_fixture_context.call_count == 2
            calls = mock_tracker.set_fixture_context.call_args_list
            assert calls[0] == ((mock_fixturedef, mock_request, "teardown"),)
            assert calls[1] == ((None, None, ""),)


class TestReportGeneration:
    """Test test report generation and assertion capture."""

    def test_pytest_runtest_makereport_passed(self, mock_test_item):
        """Test makereport hook for passed test."""
        mock_call = MagicMock()
        mock_call.excinfo = None

        with patch("pytest_junit_logging.plugin.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_get_capture.return_value = mock_capture

            result = pytest_runtest_makereport(mock_test_item, mock_call)

            # Should not add assertion logs for passed tests
            mock_capture.add_assertion_log.assert_not_called()
            assert result is None  # Hook doesn't modify report

    def test_pytest_runtest_makereport_failed_with_assertion(self, mock_test_item):
        """Test makereport hook for failed test with assertion."""
        # Create mock exception info for assertion error
        mock_excinfo = MagicMock()
        mock_excinfo.type = AssertionError
        mock_excinfo.value = AssertionError("assert 1 == 2")

        # Mock the traceback
        mock_tb = MagicMock()
        mock_tb.path = "/test/path.py"
        mock_tb.lineno = 42
        mock_excinfo.traceback = [mock_tb]

        mock_call = MagicMock()
        mock_call.when = "call"
        mock_call.excinfo = mock_excinfo

        with patch("pytest_junit_logging.plugin.get_log_capture") as mock_get_capture:
            with patch("pytest_junit_logging.plugin.get_test_tracker") as mock_get_tracker:
                with patch("pytest_junit_logging.plugin.datetime") as mock_datetime:
                    mock_capture = MagicMock()
                    mock_capture.logs = []
                    mock_tracker = MagicMock()
                    mock_tracker.get_test_item_id.return_value = "tests.test_example.test_method"
                    mock_get_capture.return_value = mock_capture
                    mock_get_tracker.return_value = mock_tracker
                    mock_datetime.now.return_value.isoformat.return_value = (
                        "2025-11-27T10:00:00+00:00"
                    )

                    result = pytest_runtest_makereport(mock_test_item, mock_call)

                    # Should append to logs list
                    assert len(mock_capture.logs) == 1
                    assert mock_capture.logs[0].level == "ASSERT"
                    assert mock_capture.logs[0].message == "assert 1 == 2"
                    assert result is None

    def test_pytest_runtest_makereport_failed_with_other_exception(self, mock_test_item):
        """Test makereport hook for failed test with non-assertion error."""
        mock_excinfo = MagicMock()
        mock_excinfo.type = ValueError
        mock_excinfo.value = ValueError("Some other error")

        mock_call = MagicMock()
        mock_call.excinfo = mock_excinfo

        with patch("pytest_junit_logging.plugin.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_get_capture.return_value = mock_capture

            result = pytest_runtest_makereport(mock_test_item, mock_call)

            # Should not add assertion logs for non-assertion errors
            mock_capture.add_assertion_log.assert_not_called()
            assert result is None


class TestSessionFinalization:
    """Test session finalization and XML modification."""

    def test_pytest_sessionfinish_with_xml_file(self, temp_dir):
        """Test session finish hook with XML file processing."""
        # Create sample XML file
        xml_content = """<?xml version='1.0' encoding='utf-8'?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="2" time="0.02">
        <testcase classname="tests.test_example.TestClass" name="test_method_a" time="0.001" />
        <testcase classname="tests.test_example.TestClass" name="test_method_b" time="0.001" />
    </testsuite>
</testsuites>"""

        xml_file = temp_dir / "results.xml"
        xml_file.write_text(xml_content)

        # Mock session with XML path
        session = MagicMock()
        session.config.option.xmlpath = str(xml_file)

        # Mock exitstatus
        exitstatus = 0

        with patch("pytest_junit_logging.plugin.add_logs_to_testcase") as mock_add_logs:
            pytest_sessionfinish(session, exitstatus)

            # Should process each testcase
            assert mock_add_logs.call_count == 2

            call(
                mock_add_logs.call_args_list[0][0][0],
                "tests.test_example.TestClass.test_method_a",
            )
            call(
                mock_add_logs.call_args_list[1][0][0],
                "tests.test_example.TestClass.test_method_b",
            )

            # Verify XML file was processed correctly
            tree = ET.parse(xml_file)
            testcases = tree.findall(".//testcase")
            assert len(testcases) == 2

    def test_pytest_sessionfinish_without_xml_file(self):
        """Test session finish hook when no XML file is configured."""
        session = MagicMock()
        session.config.option.xmlpath = None
        exitstatus = 0

        with patch("pytest_junit_logging.plugin.add_logs_to_testcase") as mock_add_logs:
            pytest_sessionfinish(session, exitstatus)

            # Should not process anything
            mock_add_logs.assert_not_called()

    def test_pytest_sessionfinish_nonexistent_xml_file(self):
        """Test session finish hook when XML file doesn't exist."""
        session = MagicMock()
        session.config.option.xmlpath = "/nonexistent/path/results.xml"
        exitstatus = 0

        with patch("pytest_junit_logging.plugin.add_logs_to_testcase") as mock_add_logs:
            # Should not raise exception, just skip processing
            pytest_sessionfinish(session, exitstatus)
            mock_add_logs.assert_not_called()


class TestCompleteHookIntegration:
    """Test complete hook integration scenarios."""

    def test_full_test_lifecycle_integration(self, mock_test_item, mock_fixturedef, mock_request):
        """Test complete test lifecycle with all hooks."""
        with patch("pytest_junit_logging.plugin.get_test_tracker") as mock_get_tracker:
            with patch("pytest_junit_logging.plugin.get_log_capture") as mock_get_capture:
                mock_tracker = MagicMock()
                mock_capture = MagicMock()
                mock_get_tracker.return_value = mock_tracker
                mock_get_capture.return_value = mock_capture

                # Simulate complete test lifecycle

                # 1. Fixture setup
                pytest_fixture_setup(mock_fixturedef, mock_request)

                # 2. Test setup
                pytest_runtest_setup(mock_test_item)

                # 3. Test call
                pytest_runtest_call(mock_test_item)

                # 4. Test teardown
                mock_nextitem = MagicMock()
                pytest_runtest_teardown(mock_test_item, mock_nextitem)

                # 5. Fixture teardown
                pytest_fixture_post_finalizer(mock_fixturedef, mock_request)

                # Verify correct hook sequence
                expected_tracker_calls = [
                    call.set_fixture_context(mock_fixturedef, mock_request, "setup"),
                    call.set_current_test_item(mock_test_item),
                    call.set_fixture_context(mock_fixturedef, mock_request, "teardown"),
                    call.set_fixture_context(None, None, ""),
                ]
                assert mock_tracker.method_calls == expected_tracker_calls

    def test_parametrized_test_handling(self, mock_parametrized_item):
        """Test handling of parametrized tests."""
        with patch("pytest_junit_logging.plugin.get_test_tracker") as mock_get_tracker:
            mock_tracker = MagicMock()
            mock_get_tracker.return_value = mock_tracker

            # Test that parametrized items are handled correctly
            pytest_runtest_setup(mock_parametrized_item)

            mock_tracker.set_current_test_item.assert_called_once_with(mock_parametrized_item)

    def test_error_handling_in_hooks(self, mock_test_item):
        """Test that hooks handle errors gracefully."""
        with patch("pytest_junit_logging.plugin.get_test_tracker") as mock_get_tracker:
            # Make tracker raise exception
            mock_tracker = MagicMock()
            mock_tracker.set_current_test_item.side_effect = Exception("Tracker error")
            mock_get_tracker.return_value = mock_tracker

            # Hooks should not propagate exceptions
            try:
                pytest_runtest_setup(mock_test_item)
                # Should not raise, hook should handle gracefully
            except Exception:
                pytest.fail("Hook should handle exceptions gracefully")
