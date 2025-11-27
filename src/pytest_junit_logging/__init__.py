"""
pytest-junit-logging: A pytest plugin for embedding log output into JUnit XML reports.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pytest-junit-logging")
except PackageNotFoundError:
    __version__ = "unknown"