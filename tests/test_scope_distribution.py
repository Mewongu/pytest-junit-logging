"""
Tests for fixture scope distribution logic.
"""

from unittest.mock import MagicMock, patch

from pytest_junit_logging.log_capture import LogEntry


class TestScopeDistribution:
    """Test fixture scope-based log distribution."""

    def test_session_logs_appear_in_all_tests(self, test_tracker):
        """Test that session scope logs appear in all test cases."""
        # Create session fixture logs
        session_logs = [
            LogEntry(
                timestamp="2025-11-27T10:00:00.000000+00:00",
                level="INFO",
                message="Session fixture initializing",
                logger_name="conftest.session",
                filename="/workspace/conftest.py",
                lineno=10,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="session",
                fixture_phase="setup",
            ),
            LogEntry(
                timestamp="2025-11-27T10:05:00.000000+00:00",
                level="INFO",
                message="Session fixture terminating",
                logger_name="conftest.session",
                filename="/workspace/conftest.py",
                lineno=15,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="session",
                fixture_phase="teardown",
            ),
        ]

        # Mock log capture to return our session logs
        with patch("pytest_junit_logging.log_capture.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_capture.logs = session_logs
            mock_get_capture.return_value = mock_capture

            # Test that session logs appear in different test cases
            test_cases = [
                "tests.test_module_a.TestClassA.test_a",
                "tests.test_module_a.TestClassA.test_b",
                "tests.test_module_b.TestClassB.test_c",
            ]

            for test_id in test_cases:
                logs = test_tracker.associate_logs_with_test(test_id)
                session_log_messages = [
                    log.message for log in logs if log.fixture_scope == "session"
                ]
                assert "Session fixture initializing" in session_log_messages
                assert "Session fixture terminating" in session_log_messages

    def test_module_logs_appear_only_in_same_module(self, test_tracker):
        """Test that module scope logs appear only in tests from the same module."""
        # Create module fixture logs
        module_logs = [
            LogEntry(
                timestamp="2025-11-27T10:01:00.000000+00:00",
                level="INFO",
                message="Module fixture initializing",
                logger_name="conftest.module",
                filename="/workspace/conftest.py",
                lineno=20,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="module",
                fixture_phase="setup",
            )
        ]

        with patch("pytest_junit_logging.log_capture.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_capture.logs = module_logs
            mock_get_capture.return_value = mock_capture

            # Should appear in same module tests
            logs_module_a = test_tracker.associate_logs_with_test(
                "tests.test_module_a.TestClassA.test_a"
            )
            module_log_messages = [
                log.message for log in logs_module_a if log.fixture_scope == "module"
            ]
            assert "Module fixture initializing" in module_log_messages

            # Should NOT appear in different module tests
            logs_module_b = test_tracker.associate_logs_with_test(
                "tests.test_module_b.TestClassB.test_c"
            )
            module_log_messages = [
                log.message for log in logs_module_b if log.fixture_scope == "module"
            ]
            assert "Module fixture initializing" not in module_log_messages

    def test_function_logs_appear_only_in_specific_test(self, test_tracker):
        """Test that function scope logs appear only in the specific test."""
        # Create function fixture logs
        function_logs = [
            LogEntry(
                timestamp="2025-11-27T10:02:00.000000+00:00",
                level="INFO",
                message="Function fixture initializing",
                logger_name="conftest.function",
                filename="/workspace/conftest.py",
                lineno=30,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="function",
                fixture_phase="setup",
            )
        ]

        with patch("pytest_junit_logging.log_capture.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_capture.logs = function_logs
            mock_get_capture.return_value = mock_capture

            # Should appear in the specific test
            logs_specific = test_tracker.associate_logs_with_test(
                "tests.test_module_a.TestClassA.test_a"
            )
            function_log_messages = [
                log.message for log in logs_specific if log.fixture_scope == "function"
            ]
            assert "Function fixture initializing" in function_log_messages

            # Should NOT appear in other tests
            logs_other = test_tracker.associate_logs_with_test(
                "tests.test_module_a.TestClassA.test_b"
            )
            function_log_messages = [
                log.message for log in logs_other if log.fixture_scope == "function"
            ]
            assert "Function fixture initializing" not in function_log_messages

    def test_regular_test_logs_appear_only_in_own_test(self, test_tracker):
        """Test that regular test logs appear only in their own test."""
        # Create regular test logs (no fixture scope)
        test_logs = [
            LogEntry(
                timestamp="2025-11-27T10:03:00.000000+00:00",
                level="DEBUG",
                message="Test execution log",
                logger_name="test.execution",
                filename="/workspace/test_module_a.py",
                lineno=10,
                test_item_id="tests.test_module_a.TestClassA.test_a",
            )
        ]

        with patch("pytest_junit_logging.log_capture.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_capture.logs = test_logs
            mock_get_capture.return_value = mock_capture

            # Should appear in the specific test
            logs_specific = test_tracker.associate_logs_with_test(
                "tests.test_module_a.TestClassA.test_a"
            )
            test_log_messages = [log.message for log in logs_specific if not log.fixture_scope]
            assert "Test execution log" in test_log_messages

            # Should NOT appear in other tests
            logs_other = test_tracker.associate_logs_with_test(
                "tests.test_module_a.TestClassA.test_b"
            )
            test_log_messages = [log.message for log in logs_other if not log.fixture_scope]
            assert "Test execution log" not in test_log_messages

    def test_parametrized_test_logs_isolated(self, test_tracker):
        """Test that parametrized test logs are properly isolated."""
        # Create logs for parametrized tests
        param_logs = [
            LogEntry(
                timestamp="2025-11-27T10:04:00.000000+00:00",
                level="DEBUG",
                message="Parametrized test log param1",
                logger_name="test.param1",
                filename="/workspace/test_module_b.py",
                lineno=15,
                test_item_id="tests.test_module_b.TestClassB.test_method[param1]",
            ),
            LogEntry(
                timestamp="2025-11-27T10:04:30.000000+00:00",
                level="DEBUG",
                message="Parametrized test log param2",
                logger_name="test.param2",
                filename="/workspace/test_module_b.py",
                lineno=15,
                test_item_id="tests.test_module_b.TestClassB.test_method[param2]",
            ),
        ]

        with patch("pytest_junit_logging.log_capture.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_capture.logs = param_logs
            mock_get_capture.return_value = mock_capture

            # First parametrized test should only see its own logs
            logs_param1 = test_tracker.associate_logs_with_test(
                "tests.test_module_b.TestClassB.test_method[param1]"
            )
            messages = [log.message for log in logs_param1]
            assert "Parametrized test log param1" in messages
            assert "Parametrized test log param2" not in messages

            # Second parametrized test should only see its own logs
            logs_param2 = test_tracker.associate_logs_with_test(
                "tests.test_module_b.TestClassB.test_method[param2]"
            )
            messages = [log.message for log in logs_param2]
            assert "Parametrized test log param2" in messages
            assert "Parametrized test log param1" not in messages

    def test_mixed_scope_logs_chronological_order(self, test_tracker):
        """Test that mixed scope logs maintain chronological order."""
        # Create logs with different scopes but ordered timestamps
        mixed_logs = [
            LogEntry(
                timestamp="2025-11-27T10:00:00.000000+00:00",
                level="INFO",
                message="1. Session setup",
                logger_name="conftest.session",
                filename="/workspace/conftest.py",
                lineno=10,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="session",
                fixture_phase="setup",
            ),
            LogEntry(
                timestamp="2025-11-27T10:00:01.000000+00:00",
                level="INFO",
                message="2. Module setup",
                logger_name="conftest.module",
                filename="/workspace/conftest.py",
                lineno=20,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="module",
                fixture_phase="setup",
            ),
            LogEntry(
                timestamp="2025-11-27T10:00:02.000000+00:00",
                level="INFO",
                message="3. Function setup",
                logger_name="conftest.function",
                filename="/workspace/conftest.py",
                lineno=30,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="function",
                fixture_phase="setup",
            ),
            LogEntry(
                timestamp="2025-11-27T10:00:03.000000+00:00",
                level="DEBUG",
                message="4. Test execution",
                logger_name="test.execution",
                filename="/workspace/test_module_a.py",
                lineno=10,
                test_item_id="tests.test_module_a.TestClassA.test_a",
            ),
            LogEntry(
                timestamp="2025-11-27T10:00:04.000000+00:00",
                level="INFO",
                message="5. Function teardown",
                logger_name="conftest.function",
                filename="/workspace/conftest.py",
                lineno=35,
                test_item_id="tests.test_module_a.TestClassA.test_a",
                fixture_scope="function",
                fixture_phase="teardown",
            ),
        ]

        with patch("pytest_junit_logging.log_capture.get_log_capture") as mock_get_capture:
            mock_capture = MagicMock()
            mock_capture.logs = mixed_logs
            mock_get_capture.return_value = mock_capture

            logs = test_tracker.associate_logs_with_test("tests.test_module_a.TestClassA.test_a")

            # Verify chronological order
            messages = [log.message for log in logs]
            expected_order = [
                "1. Session setup",
                "2. Module setup",
                "3. Function setup",
                "4. Test execution",
                "5. Function teardown",
            ]
            assert messages == expected_order

    def test_module_id_extraction(self, test_tracker):
        """Test module ID extraction from test item IDs."""
        test_cases = [
            ("tests.test_module_a.TestClassA.test_method", "tests.test_module_a"),
            ("tests.test_module_b.TestClassB.test_method[param]", "tests.test_module_b"),
            ("simple_module.test_function", "simple_module.test_function"),  # Fallback case
        ]

        for test_id, expected_module in test_cases:
            module_id = test_tracker._get_module_from_test_id(test_id)
            assert module_id == expected_module
