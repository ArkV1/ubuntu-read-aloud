.PHONY: test clean install lint all help

# Default target executed when no arguments are given to make
all: test

help:
	@echo "Available targets:"
	@echo "  test       - Run all tests"
	@echo "  unittest   - Run unit tests only"
	@echo "  clean      - Remove Python cache files"
	@echo "  install    - Install the package"
	@echo "  lint       - Run linting checks"
	@echo "  all        - Run tests (default)"
	@echo "  help       - Show this help"

# Run all tests
test:
	python -m pytest

# Run unit tests only (not integration or requiring display)
unittest:
	python -m pytest -m "not integration and not requires_display"

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +

# Install the package
install:
	pip install -e .

# Run linting
lint:
	pylint src tests || true
	flake8 src tests || true 