"""
Test configuration and fixtures for pytest-junit-logging tests.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pytest_junit_logging.log_capture import LogEntry, TestItemTracker, TestLogCapture


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_test_item():
    """Create a mock pytest test item."""
    item = MagicMock()
    item.nodeid = "tests/test_example.py::TestClass::test_method"
    item.name = "test_method"
    item.cls = MagicMock()
    item.cls.__name__ = "TestClass"
    item.module = MagicMock()
    item.module.__name__ = "test_example"
    return item


@pytest.fixture
def mock_parametrized_item():
    """Create a mock parametrized pytest test item."""
    item = MagicMock()
    item.nodeid = "tests/test_example.py::TestClass::test_method[param1]"
    item.name = "test_method[param1]"
    item.cls = MagicMock()
    item.cls.__name__ = "TestClass"
    item.module = MagicMock()
    item.module.__name__ = "test_example"
    return item


@pytest.fixture
def sample_log_entry():
    """Create a sample log entry for testing."""
    return LogEntry(
        timestamp="2025-11-27T10:00:00.000000+00:00",
        level="INFO",
        message="Test log message",
        filename="/workspace/tests/test_example.py",
        lineno=42,
        test_item_id="tests.test_example.TestClass.test_method",
    )


@pytest.fixture
def log_capture():
    """Create a fresh TestLogCapture instance."""
    capture = TestLogCapture()
    yield capture
    # Cleanup
    capture.logs.clear()


@pytest.fixture
def test_tracker():
    """Create a fresh TestItemTracker instance."""
    return TestItemTracker()


@pytest.fixture
def mock_fixturedef():
    """Create a mock pytest fixture definition."""
    fixturedef = MagicMock()
    fixturedef.argname = "test_fixture"
    fixturedef.scope = "function"
    return fixturedef


@pytest.fixture
def mock_request():
    """Create a mock pytest fixture request."""
    request = MagicMock()
    node = MagicMock()
    node.nodeid = "tests/test_example.py::TestClass::test_method"
    request.node = node
    return request
