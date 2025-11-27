"""
Log capture infrastructure for pytest-junit-logging.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class LogEntry:
    """Represents a captured log entry with metadata."""

    timestamp: str
    level: str
    message: str
    filename: str
    lineno: int
    test_item_id: str | None = None
    fixture_scope: str | None = None
    fixture_phase: str | None = None


class TestLogCapture(logging.Handler):
    """Custom logging handler that captures logs during test execution."""

    def __init__(self):
        super().__init__()
        self.logs: list[LogEntry] = []
        self.current_test_item: str | None = None
        self.current_fixture_context: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def set_current_test_item(self, test_item_id: str | None) -> None:
        """Set the current test item context for log association."""
        with self._lock:
            self.current_test_item = test_item_id

    def set_fixture_context(self, fixture_context: dict[str, Any] | None) -> None:
        """Set the current fixture context for log association."""
        with self._lock:
            self.current_fixture_context = fixture_context

    def emit(self, record: logging.LogRecord) -> None:
        """Capture a log record and store it with metadata."""
        # Check if record meets the handler's level requirement
        if record.levelno < self.level:
            return

        try:
            # Format timestamp in ISO format with timezone
            timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

            # Extract source file and line number
            filename = record.pathname
            lineno = record.lineno

            # Get the formatted message
            message = self.format(record)

            # Determine the appropriate test item ID based on context
            test_item_id = self._determine_test_context()

            # Create log entry
            log_entry = LogEntry(
                timestamp=timestamp,
                level=record.levelname,
                message=message,
                filename=filename,
                lineno=lineno,
                test_item_id=test_item_id,
            )

            with self._lock:
                self.logs.append(log_entry)

            # If we're in a fixture context, also add to scope-specific collections
            if self.current_fixture_context:
                self._add_to_fixture_scope(log_entry)

        except Exception:
            # Don't let logging errors break the test
            pass

    def _determine_test_context(self) -> str | None:
        """Determine the appropriate test context for a log entry."""
        if self.current_fixture_context and "test_item_id" in self.current_fixture_context:
            # During fixture execution, use the test item from fixture context
            return self.current_fixture_context.get("test_item_id")
        else:
            # During test execution, use the current test item
            return self.current_test_item

    def _add_to_fixture_scope(self, log_entry: LogEntry) -> None:
        """Add log entry to the appropriate fixture scope collection."""
        # Store fixture context info in the log entry for later processing
        # We'll handle the scope distribution in the tracker
        if self.current_fixture_context:
            log_entry.fixture_scope = self.current_fixture_context["scope"]
            log_entry.fixture_phase = self.current_fixture_context["phase"]

    def get_logs_for_test(self, test_item_id: str) -> list[LogEntry]:
        """Get all logs associated with a specific test item."""
        with self._lock:
            return [log for log in self.logs if log.test_item_id == test_item_id]

    def clear_logs(self) -> None:
        """Clear all captured logs."""
        with self._lock:
            self.logs.clear()


# Global log capture instance
_log_capture: TestLogCapture | None = None


def get_log_capture() -> TestLogCapture:
    """Get the global log capture instance."""
    global _log_capture
    if _log_capture is None:
        _log_capture = TestLogCapture()
    return _log_capture


def install_log_capture(min_level: int = logging.DEBUG) -> None:
    """Install the log capture handler to the root logger.

    Args:
        min_level: Minimum log level to capture (default: DEBUG)
    """
    capture = get_log_capture()
    root_logger = logging.getLogger()

    # Only add if not already added
    if capture not in root_logger.handlers:
        root_logger.addHandler(capture)
        capture.setLevel(min_level)
        # Ensure root logger level allows our logs through
        if root_logger.level > min_level:
            root_logger.setLevel(min_level)


def uninstall_log_capture() -> None:
    """Remove the log capture handler from the root logger."""
    capture = get_log_capture()
    root_logger = logging.getLogger()

    if capture in root_logger.handlers:
        root_logger.removeHandler(capture)


class TestItemTracker:
    """Tracks test item context and manages log association."""

    def __init__(self):
        self.current_test_item: str | None = None
        self.current_fixture_context: dict[str, Any] | None = None
        self.session_logs: list[LogEntry] = []
        self.module_logs: dict[str, list[LogEntry]] = {}
        self.test_logs: dict[str, list[LogEntry]] = {}
        self._lock = threading.Lock()

    def get_test_item_id(self, item) -> str:  # type: ignore[no-untyped-def]
        """Generate a unique ID for a test item."""
        # Match the format used by pytest's JUnit XML plugin
        # Use the full nodeid to get the package path
        parts = item.nodeid.split("::")
        module_path = parts[0].replace("/", ".").replace(".py", "")

        if item.cls:
            return f"{module_path}.{item.cls.__name__}.{item.name}"
        else:
            return f"{module_path}.{item.name}"

    def get_module_id(self, item) -> str:  # type: ignore[no-untyped-def]
        """Get the module ID for a test item."""
        return item.module.__name__  # type: ignore[no-any-return]

    def set_current_test_item(self, item) -> None:  # type: ignore[no-untyped-def]
        """Set the current test item context."""
        with self._lock:
            if item:
                self.current_test_item = self.get_test_item_id(item)
            else:
                self.current_test_item = None

        # Update log capture handler
        get_log_capture().set_current_test_item(self.current_test_item)

    def set_fixture_context(self, fixturedef, request, phase: str) -> None:  # type: ignore[no-untyped-def]
        """Set the current fixture context for log capture."""
        with self._lock:
            if fixturedef and request:
                # For fixtures, we need to determine which test item they're associated with
                test_item = getattr(request, "node", None)
                test_item_id = None
                if test_item and hasattr(test_item, "nodeid"):
                    # Generate test ID from the request node
                    test_item_id = self._generate_test_id_from_node(test_item)

                self.current_fixture_context = {
                    "name": fixturedef.argname,
                    "scope": fixturedef.scope,
                    "phase": phase,  # "setup" or "teardown"
                    "request": request,
                    "test_item_id": test_item_id,
                }

                # Temporarily set the current test item if not set
                if not self.current_test_item and test_item_id:
                    self.current_test_item = test_item_id
            else:
                self.current_fixture_context = None

        # Update log capture handler with fixture context
        get_log_capture().set_fixture_context(self.current_fixture_context)

    def _generate_test_id_from_node(self, node) -> str:  # type: ignore[no-untyped-def]
        """Generate test ID from a pytest node."""
        # Similar to get_test_item_id but from a node
        nodeid = node.nodeid
        parts = nodeid.split("::")
        module_path: str = parts[0].replace("/", ".").replace(".py", "")

        if len(parts) >= 3:  # module::class::test
            class_name = parts[1]
            test_name = parts[2]
            return f"{module_path}.{class_name}.{test_name}"
        elif len(parts) >= 2:  # module::test
            test_name = parts[1]
            return f"{module_path}.{test_name}"
        else:
            return module_path

    def associate_logs_with_test(self, test_item_id: str) -> list[LogEntry]:
        """Get all logs that should be associated with a test item."""
        with self._lock:
            all_logs = []

            # Get all logs from the capture handler
            capture = get_log_capture()
            all_captured_logs = capture.logs.copy()

            # Process logs and distribute by scope
            for log in all_captured_logs:
                should_include = False

                if log.fixture_scope == "session":
                    # Session fixture logs appear in all tests
                    should_include = True
                elif log.fixture_scope == "module":
                    # Module fixture logs appear in tests from the same module
                    log_module = self._get_module_from_test_id(log.test_item_id or "")
                    test_module = self._get_module_from_test_id(test_item_id)
                    should_include = log_module == test_module
                elif log.fixture_scope == "function":
                    # Function fixture logs appear only in the specific test
                    should_include = log.test_item_id == test_item_id
                elif log.test_item_id == test_item_id:
                    # Regular test logs (not from fixtures)
                    should_include = True

                if should_include:
                    all_logs.append(log)

            # Sort by timestamp to maintain chronological order
            all_logs.sort(key=lambda log: log.timestamp)

            return all_logs

    def _get_module_from_test_id(self, test_id: str) -> str:
        """Extract module name from test item ID."""
        # test_id format: "tests.test_module_a.TestClassA.test_a"
        parts = test_id.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:2])  # "tests.test_module_a"
        return test_id


# Global test item tracker
_test_tracker: TestItemTracker | None = None


def get_test_tracker() -> TestItemTracker:
    """Get the global test item tracker."""
    global _test_tracker
    if _test_tracker is None:
        _test_tracker = TestItemTracker()
    return _test_tracker
