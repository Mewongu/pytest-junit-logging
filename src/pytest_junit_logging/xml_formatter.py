"""
JUnit XML formatting with log integration.
"""

import xml.etree.ElementTree as ET
from typing import List
from .log_capture import LogEntry, get_test_tracker
import html
import os


def format_log_entry_for_xml(log_entry: LogEntry) -> ET.Element:
    """Format a log entry as an XML element."""
    log_element = ET.Element("log")
    
    # Set step attribute based on fixture phase
    if log_entry.fixture_phase == "setup":
        step = "setup"
    elif log_entry.fixture_phase == "teardown":
        step = "teardown"
    else:
        step = "test"
    log_element.set("step", step)
    
    # Set attributes
    log_element.set("ts", log_entry.timestamp)
    log_element.set("level", log_entry.level)
    
    # Format source location (file:line) with relative path from project root
    relative_path = _get_relative_path(log_entry.filename)
    log_element.set("src", f"{relative_path}:{log_entry.lineno}")
    
    # Set the log message as text content (escape HTML entities)
    log_element.text = html.escape(log_entry.message)
    
    return log_element


def _get_relative_path(full_path: str) -> str:
    """Convert absolute path to relative path from project root."""
    try:
        # Get current working directory as project root
        cwd = os.getcwd()
        
        # If the path is within the project, make it relative
        if full_path.startswith(cwd):
            relative = os.path.relpath(full_path, cwd)
            return relative
        else:
            # If outside project, just return basename
            return os.path.basename(full_path)
    except (ValueError, OSError):
        # Fallback to basename if path operations fail
        return os.path.basename(full_path)


def add_logs_to_testcase(testcase_element: ET.Element, test_item_id: str) -> None:
    """Add logs section to a testcase XML element."""
    tracker = get_test_tracker()
    logs = tracker.associate_logs_with_test(test_item_id)
    
    if logs:
        # Create logs container element
        logs_element = ET.SubElement(testcase_element, "logs")
        
        # Add each log entry
        for log_entry in logs:
            log_xml = format_log_entry_for_xml(log_entry)
            logs_element.append(log_xml)


def get_testcase_id_from_element(testcase_element: ET.Element) -> str:
    """Extract test item ID from a testcase XML element."""
    classname = testcase_element.get("classname", "")
    name = testcase_element.get("name", "")
    
    # Combine classname and name - the XML already has the correct format
    if classname:
        return f"{classname}.{name}"
    else:
        return name