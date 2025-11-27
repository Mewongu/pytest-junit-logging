# pytest-junit-logging

A pytest plugin that captures log output during test execution and embeds it into JUnit XML reports.

## Features

- 📋 **Log Integration**: Automatically captures all log output during test execution and embeds it into JUnit XML reports
- 🎯 **Smart Scope Distribution**: Session-scoped logs appear in all tests, module-scoped logs appear in module tests, function-scoped logs appear only in specific tests
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
                <log ts="2025-11-27T10:00:00.000000+00:00" level="INFO" src="test_example.py:8">Setting up database connection</log>
                <log ts="2025-11-27T10:00:00.100000+00:00" level="INFO" src="test_example.py:15">Starting user creation test</log>
                <log ts="2025-11-27T10:00:00.200000+00:00" level="INFO" src="test_example.py:22">User creation test completed successfully</log>
            </logs>
        </testcase>
        <testcase classname="test_example" name="test_user_validation" time="0.001">
            <logs>
                <log ts="2025-11-27T10:00:01.000000+00:00" level="INFO" src="test_example.py:8">Setting up database connection</log>
                <log ts="2025-11-27T10:00:01.100000+00:00" level="WARNING" src="test_example.py:25">This is a validation test</log>
                <log ts="2025-11-27T10:00:01.200000+00:00" level="INFO" src="test_example.py:10">Closing database connection</log>
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

## License

MIT License - see LICENSE file for details.
