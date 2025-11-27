"""
Log capture infrastructure for pytest-junit-logging.
"""

import logging
import time
import threading
from typing import List, Dict, Optional, Any
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


def uninstall_log_capture() -> None:
    """Remove the log capture handler from the root logger."""
    capture = get_log_capture()
    root_logger = logging.getLogger()
    
    if capture in root_logger.handlers:
        root_logger.removeHandler(capture)