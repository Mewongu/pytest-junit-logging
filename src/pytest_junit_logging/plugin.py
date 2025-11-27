"""
Core pytest-junit-logging plugin implementation.
"""

import pytest
import logging
from .log_capture import (
    install_log_capture, 
    uninstall_log_capture, 
    get_test_tracker,
    get_log_capture,
    LogEntry
)
from .xml_formatter import add_logs_to_testcase, get_testcase_id_from_element
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def pytest_addoption(parser):
    """Add plugin-specific command line options."""
    group = parser.getgroup("junit-logging", "JUnit XML log integration")
    group.addoption(
        "--junit-log-level",
        action="store",
        default="DEBUG",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Minimum log level to include in JUnit XML (default: DEBUG)"
    )


def pytest_configure(config):
    """Called after command line options have been parsed."""
    # Verify plugin is loaded
    if hasattr(config, '_store'):
        config._store["pytest_junit_logging_loaded"] = True
    
    # Only install if junit-xml is enabled
    if hasattr(config.option, "xmlpath") and config.option.xmlpath:
        # Get the log level configuration
        log_level_str = getattr(config.option, "junit_log_level", "DEBUG")
        log_level = getattr(logging, log_level_str)
        
        # Install log capture handler with the specified level
        install_log_capture(log_level)


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    # Clear any previous logs
    get_log_capture().clear_logs()


def pytest_runtest_setup(item):
    """Called before each test item is executed."""
    try:
        tracker = get_test_tracker()
        tracker.set_current_test_item(item)
    except Exception:
        # Don't let plugin errors break test execution
        pass


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


def pytest_fixture_setup(fixturedef, request):
    """Called before each fixture is executed."""
    try:
        tracker = get_test_tracker()
        tracker.set_fixture_context(fixturedef, request, "setup")
    except Exception:
        # Don't let plugin errors break test execution
        pass


def pytest_fixture_post_finalizer(fixturedef, request):
    """Called after each fixture finalizer is executed."""
    try:
        tracker = get_test_tracker()
        tracker.set_fixture_context(fixturedef, request, "teardown")
        
        # Clear fixture context after finalizer
        tracker.set_fixture_context(None, None, "")
    except Exception:
        # Don't let plugin errors break test execution
        pass


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    # Modify JUnit XML if it was generated
    if hasattr(session.config, "option") and hasattr(session.config.option, "xmlpath"):
        xmlpath = session.config.option.xmlpath
        if xmlpath:
            modify_junit_xml(xmlpath)
    
    # Clean up log capture
    uninstall_log_capture()
    
    # Clear test context
    get_test_tracker().set_current_test_item(None)


def modify_junit_xml(xml_path: str) -> None:
    """Modify the generated JUnit XML to include log entries."""
    try:
        # Parse the existing XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Find all testcase elements and add logs
        for testcase in root.iter("testcase"):
            test_id = get_testcase_id_from_element(testcase)
            add_logs_to_testcase(testcase, test_id)
        
        # Pretty format the XML
        indent_xml(root)
        
        # Write back the modified XML
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        
    except Exception as e:
        # Don't let XML modification errors break the test run
        print(f"Warning: Failed to modify JUnit XML: {e}")


def indent_xml(elem, level=0):
    """Add pretty-printing indentation to XML elements."""
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent_xml(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i