"""
Core pytest-junit-logging plugin implementation.
"""

import pytest
from .log_capture import (
    install_log_capture, 
    uninstall_log_capture, 
    get_test_tracker,
    get_log_capture
)


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


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    # Clean up log capture
    uninstall_log_capture()
    
    # Clear test context
    get_test_tracker().set_current_test_item(None)