"""
Log capture infrastructure for pytest-junit-logging.
"""

import logging
import time
import threading
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class LogEntry:
    """Represents a captured log entry with metadata."""
    timestamp: str
    level: str
    message: str
    filename: str
    lineno: int
    test_item_id: Optional[str] = None
    fixture_scope: Optional[str] = None
    fixture_phase: Optional[str] = None


class TestLogCapture(logging.Handler):
    """Custom logging handler that captures logs during test execution."""
    
    def __init__(self):
        super().__init__()
        self.logs: List[LogEntry] = []
        self.current_test_item: Optional[str] = None
        self.current_fixture_context: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()
    
    def set_current_test_item(self, test_item_id: Optional[str]) -> None:
        """Set the current test item context for log association."""
        with self._lock:
            self.current_test_item = test_item_id
    
    def set_fixture_context(self, fixture_context: Optional[Dict[str, Any]]) -> None:
        """Set the current fixture context for log association."""
        with self._lock:
            self.current_fixture_context = fixture_context
    
    def emit(self, record: logging.LogRecord) -> None:
        """Capture a log record and store it with metadata."""
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
                test_item_id=test_item_id
            )
            
            with self._lock:
                self.logs.append(log_entry)
                
            # If we're in a fixture context, also add to scope-specific collections
            if self.current_fixture_context:
                self._add_to_fixture_scope(log_entry)
                
        except Exception:
            # Don't let logging errors break the test
            pass
    
    def _determine_test_context(self) -> Optional[str]:
        """Determine the appropriate test context for a log entry."""
        if self.current_fixture_context:
            # During fixture execution, use the current test item if available
            return self.current_test_item
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
    
    def get_logs_for_test(self, test_item_id: str) -> List[LogEntry]:
        """Get all logs associated with a specific test item."""
        with self._lock:
            return [log for log in self.logs if log.test_item_id == test_item_id]
    
    def clear_logs(self) -> None:
        """Clear all captured logs."""
        with self._lock:
            self.logs.clear()


# Global log capture instance
_log_capture: Optional[TestLogCapture] = None


def get_log_capture() -> TestLogCapture:
    """Get the global log capture instance."""
    global _log_capture
    if _log_capture is None:
        _log_capture = TestLogCapture()
    return _log_capture


def install_log_capture() -> None:
    """Install the log capture handler to the root logger."""
    capture = get_log_capture()
    root_logger = logging.getLogger()
    
    # Only add if not already added
    if capture not in root_logger.handlers:
        root_logger.addHandler(capture)
        capture.setLevel(logging.DEBUG)
        # Ensure root logger level allows our logs through
        if root_logger.level > logging.DEBUG:
            root_logger.setLevel(logging.DEBUG)


def uninstall_log_capture() -> None:
    """Remove the log capture handler from the root logger."""
    capture = get_log_capture()
    root_logger = logging.getLogger()
    
    if capture in root_logger.handlers:
        root_logger.removeHandler(capture)


class TestItemTracker:
    """Tracks test item context and manages log association."""
    
    def __init__(self):
        self.current_test_item: Optional[str] = None
        self.current_fixture_context: Optional[Dict[str, Any]] = None
        self.session_logs: List[LogEntry] = []
        self.module_logs: Dict[str, List[LogEntry]] = {}
        self.test_logs: Dict[str, List[LogEntry]] = {}
        self._lock = threading.Lock()
    
    def get_test_item_id(self, item) -> str:
        """Generate a unique ID for a test item."""
        # Match the format used by pytest's JUnit XML plugin
        # Use the full nodeid to get the package path
        parts = item.nodeid.split("::")
        module_path = parts[0].replace("/", ".").replace(".py", "")
        
        if item.cls:
            return f"{module_path}.{item.cls.__name__}.{item.name}"
        else:
            return f"{module_path}.{item.name}"
    
    def get_module_id(self, item) -> str:
        """Get the module ID for a test item."""
        return item.module.__name__
    
    def set_current_test_item(self, item) -> None:
        """Set the current test item context."""
        with self._lock:
            if item:
                self.current_test_item = self.get_test_item_id(item)
            else:
                self.current_test_item = None
        
        # Update log capture handler
        get_log_capture().set_current_test_item(self.current_test_item)
    
    def set_fixture_context(self, fixturedef, request, phase: str) -> None:
        """Set the current fixture context for log capture."""
        with self._lock:
            if fixturedef and request:
                self.current_fixture_context = {
                    "name": fixturedef.argname,
                    "scope": fixturedef.scope,
                    "phase": phase,  # "setup" or "teardown"
                    "request": request
                }
            else:
                self.current_fixture_context = None
        
        # Update log capture handler with fixture context
        get_log_capture().set_fixture_context(self.current_fixture_context)
    
    def associate_logs_with_test(self, test_item_id: str) -> List[LogEntry]:
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
                    should_include = (log_module == test_module)
                elif log.fixture_scope == "function":
                    # Function fixture logs appear only in the specific test
                    should_include = (log.test_item_id == test_item_id)
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
        # test_id format: "tests_example.test_module_a.TestClassA.test_a"
        parts = test_id.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:2])  # "tests_example.test_module_a"
        return test_id


# Global test item tracker
_test_tracker: Optional[TestItemTracker] = None


def get_test_tracker() -> TestItemTracker:
    """Get the global test item tracker."""
    global _test_tracker
    if _test_tracker is None:
        _test_tracker = TestItemTracker()
    return _test_tracker