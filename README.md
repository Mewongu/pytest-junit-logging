# pytest-junit-logging

[![Test](https://github.com/Mewongu/pytest-junit-logging/workflows/Test/badge.svg)](https://github.com/Mewongu/pytest-junit-logging/actions/workflows/test.yml)
[![Code Quality](https://github.com/Mewongu/pytest-junit-logging/workflows/Code%20Quality/badge.svg)](https://github.com/Mewongu/pytest-junit-logging/actions/workflows/quality.yml)
[![Integration Tests](https://github.com/Mewongu/pytest-junit-logging/workflows/Integration%20Tests/badge.svg)](https://github.com/Mewongu/pytest-junit-logging/actions/workflows/integration.yml)
[![PyPI version](https://badge.fury.io/py/pytest-junit-logging.svg)](https://badge.fury.io/py/pytest-junit-logging)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-junit-logging.svg)](https://pypi.org/project/pytest-junit-logging/)

A pytest plugin that captures log output during test execution and embeds it into JUnit XML reports.

## Features

- 📋 **Log Integration**: Automatically captures all log output during test execution and embeds it into JUnit XML reports
- 🎯 **Smart Scope Distribution**: Session-scoped logs appear in all tests, module-scoped logs appear in module tests, function-scoped logs appear only in specific tests
- ⚡ **Execution Phase Tags**: Each log entry includes a `step` attribute indicating whether it occurred during setup or test execution
- 🔧 **Configurable Log Levels**: Control verbosity with `--junit-log-level` option
- 🚨 **Assertion Capture**: Automatically captures assertion failure messages as ASSERT-level logs
- 📁 **Relative Paths**: File paths in logs are relative to project root for portability
- 🔒 **Safe HTML**: Automatically escapes HTML entities in log messages

## Installation

```bash
pip install pytest-junit-logging
```

## Usage

The plugin activates automatically when you use pytest's `--junit-xml` option:

```bash
# Basic usage - captures all logs (DEBUG level and above)
pytest --junit-xml=results.xml

# Control log verbosity
pytest --junit-xml=results.xml --junit-log-level=WARNING

# Only capture errors and critical logs
pytest --junit-xml=results.xml --junit-log-level=ERROR
```

## Command Line Options

| Option | Choices | Default | Description |
|--------|---------|---------|-------------|
| `--junit-log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `DEBUG` | Minimum log level to include in JUnit XML |

## Example

### Test Code

```python
# test_example.py
import logging
import pytest

@pytest.fixture(scope="session") 
def database():
    logging.info("Setting up database connection")
    yield "db_connection"
    logging.info("Closing database connection")

@pytest.fixture
def user_data():
    logging.debug("Creating test user data")
    return {"id": 123, "name": "Test User"}

def test_user_creation(database, user_data):
    logging.info("Starting user creation test")
    logging.debug(f"Using database: {database}")
    logging.debug(f"User data: {user_data}")
    
    # Simulate test logic
    assert user_data["id"] == 123
    
    logging.info("User creation test completed successfully")

def test_user_validation(database, user_data):
    logging.warning("This is a validation test")
    assert user_data["name"] == "Test User"
```

### Generated JUnit XML

```bash
pytest test_example.py --junit-xml=results.xml --junit-log-level=INFO
```

The resulting `results.xml` will include embedded logs:

```xml
<?xml version='1.0' encoding='utf-8'?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="2" time="0.01">
        <testcase classname="test_example" name="test_user_creation" time="0.001">
            <logs>
                <log step="setup" ts="2025-11-27T10:00:00.000000+00:00" level="INFO" src="test_example.py:8">Setting up database connection</log>
                <log step="test" ts="2025-11-27T10:00:00.100000+00:00" level="INFO" src="test_example.py:15">Starting user creation test</log>
                <log step="test" ts="2025-11-27T10:00:00.200000+00:00" level="INFO" src="test_example.py:22">User creation test completed successfully</log>
            </logs>
        </testcase>
        <testcase classname="test_example" name="test_user_validation" time="0.001">
            <logs>
                <log step="setup" ts="2025-11-27T10:00:01.000000+00:00" level="INFO" src="test_example.py:8">Setting up database connection</log>
                <log step="test" ts="2025-11-27T10:00:01.100000+00:00" level="WARNING" src="test_example.py:25">This is a validation test</log>
                <log step="test" ts="2025-11-27T10:00:01.200000+00:00" level="INFO" src="test_example.py:10">Closing database connection</log>
            </logs>
        </testcase>
    </testsuite>
</testsuites>
```

## Log Scope Distribution

The plugin intelligently distributes logs based on fixture scopes:

- **Session-scoped fixture logs**: Appear in all test cases
- **Module-scoped fixture logs**: Appear in all tests within the same module
- **Function-scoped fixture logs**: Appear only in the specific test that uses the fixture
- **Test execution logs**: Appear only in their respective test case

## Execution Phase Tags

Each log entry includes a `step` attribute that indicates during which execution phase the log was generated:

- **`step="setup"`**: Logs from fixture setup (session, module, function fixture initialization)
- **`step="test"`**: Logs from test execution and fixture teardown

This makes it easy to distinguish between infrastructure logs (fixture setup) and actual test logic:

```xml
<logs>
    <log step="setup" ts="..." level="INFO" src="conftest.py:10">Database connection established</log>
    <log step="setup" ts="..." level="INFO" src="conftest.py:25">User fixtures initialized</log>
    <log step="test" ts="..." level="DEBUG" src="test_user.py:15">Starting user validation test</log>
    <log step="test" ts="..." level="INFO" src="test_user.py:20">User validation completed</log>
    <log step="test" ts="..." level="INFO" src="conftest.py:30">Cleaning up user fixtures</log>
</logs>
```

**Post-processing**: To flatten the structure and remove step attributes for legacy compatibility, simply strip the `step="..."` attributes from log elements.

## Log Level Filtering

Control the verbosity of logs in your JUnit XML:

```bash
# Capture everything (default)
pytest --junit-xml=results.xml --junit-log-level=DEBUG

# Only warnings and above
pytest --junit-xml=results.xml --junit-log-level=WARNING

# Only errors and critical
pytest --junit-xml=results.xml --junit-log-level=ERROR
```

**Note**: `ASSERT` level logs (from assertion failures) are always included regardless of the log level filter.

## Integration with CI/CD

The plugin works seamlessly with CI/CD systems that consume JUnit XML reports:

- **GitHub Actions**: Use with `dorny/test-reporter`
- **Jenkins**: Native JUnit plugin support
- **GitLab CI**: Built-in JUnit report processing
- **Azure DevOps**: Test result publishing

## Requirements

- Python 3.10+
- pytest 6.0+

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd pytest-junit-logging

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

#### Local Testing
```bash
# Run tests for current Python version
pytest

# Run tests across all supported Python/pytest combinations (requires all Python versions)
tox

# Run specific tox environment
tox -e py312-pytest8
```

#### Docker-based Testing (Recommended)
```bash
# Run all tests across all Python versions in Docker
./scripts/test-all.sh

# Test specific Python version
./scripts/test-single.sh 3.11 8    # Python 3.11 with pytest 8.x

# Test individual components with docker-compose
docker-compose -f docker-compose.test.yml run --rm test-py310    # Python 3.10 tests
docker-compose -f docker-compose.test.yml run --rm test-quality  # Linting & coverage
docker-compose -f docker-compose.test.yml run --rm test-mindeps  # Minimum dependencies
```

### Tox Test Matrix

The project tests against these combinations:

| Python | pytest 6.x | pytest 7.x | pytest 8.x |
|--------|-------------|-------------|-------------|
| 3.10   | ✅          | ✅          | ✅          |
| 3.11   | -           | ✅          | ✅          |
| 3.12   | -           | -           | ✅          |
| 3.13   | -           | -           | ✅          |

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## CI/CD and Releases

### Automated Testing

The project uses GitHub Actions for comprehensive CI/CD:

- **Test Matrix**: Runs all tests across Python 3.10-3.13 and pytest 6.x-8.x combinations
- **Code Quality**: Automated linting (ruff), formatting (black), and type checking (mypy)  
- **Integration Tests**: End-to-end testing with real pytest runs and XML validation
- **Security Scanning**: Automated security scans with bandit
- **Coverage Reporting**: Code coverage tracking and reporting

All checks must pass before code can be merged to main.

### Releases

Releases are fully automated:

1. **Create a git tag** with version format `vX.Y.Z` (e.g., `v1.0.0`, `v2.1.3`)
2. **Push the tag** to trigger the release workflow:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. **Automated pipeline** runs:
   - Full test suite across all supported versions
   - Code quality checks
   - Package building and validation
   - PyPI publishing (using trusted publishing)
   - GitHub release creation with changelog

### Version Management

The project uses [setuptools-scm](https://github.com/pypa/setuptools_scm) for automatic version management:
- Version is automatically derived from git tags
- No manual version bumping required
- Supports semantic versioning and pre-releases (e.g., `v1.0.0-beta1`)

## License

MIT License - see LICENSE file for details.
