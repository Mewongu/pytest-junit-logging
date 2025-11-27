#!/bin/bash
# Test script for running tox in Docker across all Python versions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting comprehensive testing with Docker + Tox${NC}"
echo

# Create reports directory
mkdir -p reports

# Function to run tests and capture results
run_test() {
    local service=$1
    local description=$2
    
    echo -e "${YELLOW}Testing: $description${NC}"
    
    if docker-compose -f docker-compose.test.yml run --rm "$service"; then
        echo -e "${GREEN}✅ $description - PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $description - FAILED${NC}"
        return 1
    fi
    echo
}

# Track overall results
failed_tests=()

# Run tests for each Python version
echo -e "${YELLOW}📦 Testing Python versions...${NC}"
run_test "test-py310" "Python 3.10 (pytest 6.x, 7.x, 8.x)" || failed_tests+=("Python 3.10")
run_test "test-py311" "Python 3.11 (pytest 7.x, 8.x)" || failed_tests+=("Python 3.11")
run_test "test-py312" "Python 3.12 (pytest 8.x)" || failed_tests+=("Python 3.12")
run_test "test-py313" "Python 3.13 (pytest 8.x)" || failed_tests+=("Python 3.13")

echo -e "${YELLOW}🔍 Testing code quality...${NC}"
run_test "test-quality" "Linting, Coverage, and Integration" || failed_tests+=("Code Quality")

echo -e "${YELLOW}🔧 Testing minimum dependencies...${NC}"
run_test "test-mindeps" "Minimum Dependency Versions" || failed_tests+=("Min Dependencies")

# Summary
echo -e "${YELLOW}📊 Test Summary${NC}"
echo "=================="

if [ ${#failed_tests[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo
    echo "Reports are available in the ./reports/ directory"
    exit 0
else
    echo -e "${RED}❌ Some tests failed:${NC}"
    for test in "${failed_tests[@]}"; do
        echo -e "  - ${RED}$test${NC}"
    done
    echo
    echo "Check the output above for details."
    echo "Reports are available in the ./reports/ directory"
    exit 1
fi