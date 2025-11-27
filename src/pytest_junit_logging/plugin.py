"""
Core pytest-junit-logging plugin implementation.
"""

import pytest
from .log_capture import (
    install_log_capture, 
    uninstall_log_capture, 
    get_test_tracker,
    get_log_capture,
    LogEntry
)
import traceback
from datetime import datetime, timezone


def pytest_configure(config):
    """Called after command line options have been parsed."""
    # Verify plugin is loaded
    if hasattr(config, '_store'):
        config._store["pytest_junit_logging_loaded"] = True
    
    # Install log capture handler
    install_log_capture()


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    # Clear any previous logs
    get_log_capture().clear_logs()


def pytest_runtest_setup(item):
    """Called before each test item is executed."""
    tracker = get_test_tracker()
    tracker.set_current_test_item(item)


def pytest_runtest_call(item):
    """Called during test execution."""
    # Test item context already set in setup
    pass


def pytest_runtest_teardown(item, nextitem):
    """Called after each test item is executed."""
    # Keep test item context for now - will be cleared when next test starts
    pass


def pytest_runtest_makereport(item, call):
    """Capture test reports including assertion failures."""
    if call.when == "call" and call.excinfo:
        if call.excinfo.type == AssertionError:
            # Extract assertion message from the exception
            assertion_message = str(call.excinfo.value)
            
            if assertion_message:  # Only log if there's a custom message
                # Get the traceback to find the assertion line
                tb = call.excinfo.traceback[-1]  # Last frame is usually the assert
                filename = str(tb.path)
                lineno = tb.lineno
                
                # Create an ASSERT level log entry
                timestamp = datetime.now(tz=timezone.utc).isoformat()
                
                # Get the current test item ID
                tracker = get_test_tracker()
                test_item_id = tracker.get_test_item_id(item)
                
                log_entry = LogEntry(
                    timestamp=timestamp,
                    level="ASSERT",
                    message=assertion_message,
                    filename=filename,
                    lineno=lineno,
                    test_item_id=test_item_id
                )
                
                # Add to the log capture
                get_log_capture().logs.append(log_entry)


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    # Clean up log capture
    uninstall_log_capture()
    
    # Clear test context
    get_test_tracker().set_current_test_item(None)