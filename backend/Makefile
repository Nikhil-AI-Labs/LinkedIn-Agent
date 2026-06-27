.PHONY: test test-unit test-integration test-all test-coverage clean help

# Default target
help:
	@echo "LinkedIn AI Agent - Backend Test Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make test              - Run unit tests only (fast, default)"
	@echo "  make test-unit         - Run unit tests explicitly"
	@echo "  make test-integration  - Run integration tests (requires PostgreSQL)"
	@echo "  make test-all          - Run all tests (unit + integration)"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo "  make clean             - Clean test artifacts"
	@echo ""

# Run unit tests only (fast, mocked dependencies)
test:
	pytest tests/unit -v

# Explicit unit tests
test-unit:
	pytest tests/unit -v

# Integration tests (requires real PostgreSQL database)
test-integration:
	pytest tests/integration -v -m integration

# Run all tests
test-all:
	pytest tests/ -v

# Run with coverage report
test-coverage:
	pytest tests/unit --cov=app --cov-report=html --cov-report=term

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Lint code
lint:
	ruff check app tests
	black --check app tests

# Format code
format:
	ruff check --fix app tests
	black app tests

# Type check
typecheck:
	mypy app
