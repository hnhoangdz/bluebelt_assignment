# Makefile for Dextrends Backend Testing

# Variables
PYTHON = python
PIP = uv pip
TEST_DIR = src/tests
BACKEND_TEST_DIR = $(TEST_DIR)/backend
COVERAGE_DIR = htmlcov
REPORTS_DIR = test_reports

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

.PHONY: help install-deps check-env test test-unit test-integration test-database test-performance test-load test-coverage test-all clean coverage-report test-report lint format

help: ## Show this help message
	@echo "$(BLUE)Dextrends Backend Testing Commands$(NC)"
	@echo "=================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install-deps: ## Install testing dependencies
	@echo "$(YELLOW)Installing testing dependencies...$(NC)"
	$(PIP) install pytest pytest-asyncio pytest-cov locust httpx aiohttp psutil

check-env: ## Check test environment setup
	@echo "$(YELLOW)Checking test environment...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --check

test: ## Run all tests
	@echo "$(YELLOW)Running all tests...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --all

test-unit: ## Run unit tests only
	@echo "$(YELLOW)Running unit tests...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --unit

test-integration: ## Run integration tests only
	@echo "$(YELLOW)Running integration tests...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --integration

test-database: ## Run database tests only
	@echo "$(YELLOW)Running database tests...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --database

test-performance: ## Run performance tests only
	@echo "$(YELLOW)Running performance tests...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --performance

test-load: ## Show load testing instructions
	@echo "$(YELLOW)Load testing with Locust...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --load

test-coverage: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --coverage

test-fast: ## Run quick subset of tests
	@echo "$(YELLOW)Running fast test subset...$(NC)"
	$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/test_unit_services.py::TestAuthService::test_password_hashing -v
	$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/test_integration_api.py::TestHealthEndpoints::test_health_check -v

test-smoke: ## Run smoke tests (health + basic functionality)
	@echo "$(YELLOW)Running smoke tests...$(NC)"
	$(PYTHON) -m pytest -k "health or test_password_hashing" $(BACKEND_TEST_DIR)/ -v

test-report: ## Generate comprehensive test reports
	@echo "$(YELLOW)Generating test reports...$(NC)"
	$(PYTHON) $(TEST_DIR)/run_tests.py --report

coverage-report: ## Generate HTML coverage report
	@echo "$(YELLOW)Generating coverage report...$(NC)"
	$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/ --cov=src --cov-report=html:$(COVERAGE_DIR) --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated: $(COVERAGE_DIR)/index.html$(NC)"

lint: ## Run code linting
	@echo "$(YELLOW)Running linting...$(NC)"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/; \
	else \
		echo "$(RED)flake8 not installed. Install with: pip install flake8$(NC)"; \
	fi

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	@if command -v black >/dev/null 2>&1; then \
		black src/; \
	else \
		echo "$(RED)black not installed. Install with: pip install black$(NC)"; \
	fi

clean: ## Clean test artifacts
	@echo "$(YELLOW)Cleaning test artifacts...$(NC)"
	rm -rf $(COVERAGE_DIR)
	rm -rf $(REPORTS_DIR)
	rm -rf .coverage
	rm -rf .pytest_cache
	rm -rf **/__pycache__
	rm -rf **/*.pyc
	rm -f test.db
	rm -f coverage.xml
	rm -f junit.xml
	@echo "$(GREEN)Cleanup completed$(NC)"

# Development commands
dev-test: ## Run tests in development mode (with file watching)
	@echo "$(YELLOW)Running tests in development mode...$(NC)"
	@if command -v pytest-watch >/dev/null 2>&1; then \
		ptw $(BACKEND_TEST_DIR)/ -- -v; \
	else \
		echo "$(RED)pytest-watch not installed. Install with: pip install pytest-watch$(NC)"; \
		echo "$(YELLOW)Falling back to regular test run...$(NC)"; \
		$(MAKE) test; \
	fi

# Continuous Integration commands
ci-test: ## Run tests in CI mode
	@echo "$(YELLOW)Running CI tests...$(NC)"
	$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/ -v --tb=short --cov=src --cov-report=xml:coverage.xml --cov-report=term --junitxml=junit.xml

# Benchmark commands
benchmark: ## Run performance benchmarks
	@echo "$(YELLOW)Running performance benchmarks...$(NC)"
	$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/test_performance.py -v -m performance --tb=short

# Load testing commands
load-quick: ## Run quick load test (requires running server)
	@echo "$(YELLOW)Running quick load test...$(NC)"
	@echo "$(RED)Make sure the server is running on http://localhost:8000$(NC)"
	locust -f $(BACKEND_TEST_DIR)/test_load_locust.py --host=http://localhost:8000 --headless -u 10 -r 2 -t 30s

load-ui: ## Open Locust UI for interactive load testing
	@echo "$(YELLOW)Opening Locust UI...$(NC)"
	@echo "$(GREEN)Open http://localhost:8089 in your browser$(NC)"
	@echo "$(RED)Make sure the server is running on http://localhost:8000$(NC)"
	locust -f $(BACKEND_TEST_DIR)/test_load_locust.py --host=http://localhost:8000

# Docker testing commands
test-docker: ## Run tests in Docker environment
	@echo "$(YELLOW)Running tests in Docker...$(NC)"
	docker-compose -f docker-compose.yaml run --rm backend python src/tests/run_tests.py --all

# Debugging commands
test-debug: ## Run tests with debugging
	@echo "$(YELLOW)Running tests with debugging...$(NC)"
	$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/ -v -s --tb=long --pdb-trace

test-verbose: ## Run tests with maximum verbosity
	@echo "$(YELLOW)Running tests with maximum verbosity...$(NC)"
	$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/ -vvv --tb=long -s

# Security testing
test-security: ## Run security-focused tests
	@echo "$(YELLOW)Running security tests...$(NC)"
	$(PYTHON) -m pytest -k "auth or security" $(BACKEND_TEST_DIR)/ -v

# Specific test categories
test-rag: ## Run RAG-specific tests
	@echo "$(YELLOW)Running RAG tests...$(NC)"
	$(PYTHON) -m pytest -k "rag" $(BACKEND_TEST_DIR)/ -v

test-api: ## Run API tests only
	@echo "$(YELLOW)Running API tests...$(NC)"
	$(PYTHON) -m pytest -k "api" $(BACKEND_TEST_DIR)/ -v

# Quality checks
quality: lint test-coverage ## Run quality checks (lint + coverage)
	@echo "$(GREEN)Quality checks completed$(NC)"

# Full test suite for releases
test-release: clean install-deps test-coverage test-report ## Full test suite for releases
	@echo "$(GREEN)Release testing completed$(NC)"

# Help for specific test files
test-help: ## Show help for running specific test files
	@echo "$(BLUE)Specific Test File Examples:$(NC)"
	@echo "$(GREEN)make test-file FILE=test_unit_services.py$(NC)"
	@echo "$(GREEN)pytest src/tests/backend/test_unit_services.py::TestAuthService -v$(NC)"
	@echo "$(GREEN)pytest src/tests/backend/test_integration_api.py::TestHealthEndpoints::test_health_check -v$(NC)"

# Run specific test file
test-file: ## Run specific test file (usage: make test-file FILE=test_unit_services.py)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Usage: make test-file FILE=test_unit_services.py$(NC)"; \
	else \
		echo "$(YELLOW)Running test file: $(FILE)$(NC)"; \
		$(PYTHON) -m pytest $(BACKEND_TEST_DIR)/$(FILE) -v; \
	fi