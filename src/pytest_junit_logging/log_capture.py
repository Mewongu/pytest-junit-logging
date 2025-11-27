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


class TestLogCapture(logging.Handler):
    """Custom logging handler that captures logs during test execution."""
    
    def __init__(self):
        super().__init__()
        self.logs: List[LogEntry] = []
        self.current_test_item: Optional[str] = None
        self._lock = threading.Lock()
    
    def set_current_test_item(self, test_item_id: Optional[str]) -> None:
        """Set the current test item context for log association."""
        with self._lock:
            self.current_test_item = test_item_id
    
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
            
            # Create log entry
            log_entry = LogEntry(
                timestamp=timestamp,
                level=record.levelname,
                message=message,
                filename=filename,
                lineno=lineno,
                test_item_id=self.current_test_item
            )
            
            with self._lock:
                self.logs.append(log_entry)
                
        except Exception:
            # Don't let logging errors break the test
            pass
    
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
    
    def associate_logs_with_test(self, test_item_id: str) -> List[LogEntry]:
        """Get all logs that should be associated with a test item."""
        with self._lock:
            # Start with session logs (appear in all tests)
            all_logs = self.session_logs.copy()
            
            # Add module logs if this test is in that module
            for module_id, logs in self.module_logs.items():
                if test_item_id.startswith(module_id):
                    all_logs.extend(logs)
            
            # Add test-specific logs
            if test_item_id in self.test_logs:
                all_logs.extend(self.test_logs[test_item_id])
            
            # Add logs from the capture handler for this test
            capture_logs = get_log_capture().get_logs_for_test(test_item_id)
            all_logs.extend(capture_logs)
            
            # Sort by timestamp to maintain chronological order
            all_logs.sort(key=lambda log: log.timestamp)
            
            return all_logs


# Global test item tracker
_test_tracker: Optional[TestItemTracker] = None


def get_test_tracker() -> TestItemTracker:
    """Get the global test item tracker."""
    global _test_tracker
    if _test_tracker is None:
        _test_tracker = TestItemTracker()
    return _test_tracker