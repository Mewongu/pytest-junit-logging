#!/bin/bash
# Test script for running a specific Python version

set -e

PYTHON_VERSION=${1:-"3.10"}
PYTEST_VERSION=${2:-"8"}

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Testing Python $PYTHON_VERSION with pytest $PYTEST_VERSION in Docker${NC}"

# Create reports directory
mkdir -p reports

# Build and run the specific test
docker build \
    --build-arg PYTHON_VERSION="$PYTHON_VERSION" \
    -f Dockerfile.test \
    -t pytest-junit-logging-test:"py$PYTHON_VERSION" \
    .

docker run --rm \
    -v "$(pwd)/reports:/app/reports" \
    pytest-junit-logging-test:"py$PYTHON_VERSION" \
    tox -e "py${PYTHON_VERSION//./}-pytest$PYTEST_VERSION"

echo -e "${GREEN}✅ Test completed for Python $PYTHON_VERSION with pytest $PYTEST_VERSION${NC}"
