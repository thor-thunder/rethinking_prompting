#!/bin/bash

# Test runner script for rethinking_prompting
# See CLAUDE.md → "Run Tests" for full documentation
#
# Usage: ./run_tests.sh [options]
#
# Options:
#   --all           Run all tests with coverage
#   --fast          Run tests quickly without coverage
#   --unit          Run only unit tests
#   --coverage      Generate HTML coverage report
#   --watch         Watch mode (requires pytest-watch)
#   --help          Show help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default option
OPTION="${1:-fast}"

print_header() {
    echo -e "\n${YELLOW}======================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}======================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

case "$OPTION" in
    --all)
        print_header "Running all tests with coverage"
        python -m pytest tests/unit/test_dataset.py -v --cov=dataset --cov-report=term-missing --cov-report=html
        print_success "All tests passed! Coverage report in htmlcov/index.html"
        ;;
    --fast)
        print_header "Running tests (no coverage)"
        python -m pytest tests/unit/test_dataset.py -v
        print_success "All tests passed!"
        ;;
    --unit)
        print_header "Running unit tests"
        python -m pytest tests/unit/ -v
        print_success "Unit tests passed!"
        ;;
    --coverage)
        print_header "Generating coverage report"
        python -m pytest tests/unit/test_dataset.py --cov=dataset --cov-report=html
        echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    --watch)
        print_header "Running tests in watch mode"
        python -m pytest-watch tests/unit/test_dataset.py -v
        ;;
    --help)
        echo "Test runner for rethinking_prompting"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  --all       Run all tests with coverage (default: fast)"
        echo "  --fast      Run tests quickly without coverage"
        echo "  --unit      Run only unit tests"
        echo "  --coverage  Generate HTML coverage report"
        echo "  --watch     Run tests in watch mode"
        echo "  --help      Show this help message"
        ;;
    *)
        print_error "Unknown option: $OPTION"
        echo "Run '$0 --help' for usage information"
        exit 1
        ;;
esac
