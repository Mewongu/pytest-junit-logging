"""
Core pytest-junit-logging plugin implementation.
"""

import pytest


def pytest_configure(config):
    """Called after command line options have been parsed."""
    # Verify plugin is loaded
    if hasattr(config, '_store'):
        config._store["pytest_junit_logging_loaded"] = True


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    pass


def pytest_runtest_setup(item):
    """Called before each test item is executed."""
    pass


def pytest_runtest_call(item):
    """Called during test execution."""
    pass


def pytest_runtest_teardown(item, nextitem):
    """Called after each test item is executed."""
    pass


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    pass