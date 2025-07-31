# Dextrends Backend Testing Suite

## 🎯 Overview

Comprehensive testing infrastructure for the Dextrends backend, focusing on Python-based testing with pytest, pytest-asyncio, pytest-cov, and Locust for load testing.

## 📁 Test Structure

```
backend/tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration and fixtures
├── run_tests.py                 # Test runner script
└── backend/
    ├── test_simple.py           # Basic functionality verification
    ├── test_unit_services.py    # Unit tests for core services
    ├── test_integration_api.py  # API endpoint integration tests
    ├── test_database.py         # Database operation tests
    ├── test_performance.py      # Performance and load tests
    └── test_load_locust.py      # Locust-based load testing
```

## 🚀 Quick Start

### Prerequisites
```bash
# Install testing dependencies
uv pip install pytest pytest-asyncio pytest-cov locust httpx aiohttp psutil
```

### Running Tests

#### Using the Test Runner
```bash
# Check environment
python backend/tests/run_tests.py --check

# Run all tests
python backend/tests/run_tests.py --all

# Run specific test categories
python backend/tests/run_tests.py --unit
python backend/tests/run_tests.py --integration
python backend/tests/run_tests.py --performance

# Run with coverage
python backend/tests/run_tests.py --coverage

# Generate comprehensive reports
python backend/tests/run_tests.py --report
```

#### Using Makefile
```bash
# Check environment
make check-env

# Run all tests
make test

# Run specific categories
make test-unit
make test-integration
make test-performance

# Run with coverage
make test-coverage

# Quick tests
make test-fast
```

#### Using pytest directly
```bash
# Basic test run
pytest backend/tests/backend/ -v

# With coverage
pytest backend/tests/backend/ --cov=backend --cov-report=html

# Specific test markers
pytest backend/tests/backend/ -m unit
pytest backend/tests/backend/ -m integration
pytest backend/tests/backend/ -m performance
```

## 🧪 Test Categories

### Unit Tests (`test_unit_services.py`)
- **AuthService**: Password hashing, JWT tokens, user authentication
- **QueryProcessor**: Query rewriting, intent classification, routing
- **EmbeddingService**: Text embeddings, batch processing, similarity search
- **RAGService**: Context building, response generation, memory integration

### Integration Tests (`test_integration_api.py`)
- **Health Endpoints**: Basic health checks
- **Auth Endpoints**: Registration, login, protected routes
- **Chat Endpoints**: RAG queries, conversation history
- **User Endpoints**: Profile management, session handling
- **Analytics Endpoints**: System metrics (admin)

### Database Tests (`test_database.py`)
- **Connection Management**: Database connections, error handling
- **Model Operations**: CRUD operations for User, Conversation, Session
- **Transactions**: Commit/rollback behavior
- **Performance**: Bulk operations, concurrent access

### Performance Tests (`test_performance.py`)
- **Endpoint Performance**: Response times, throughput
- **Concurrent Users**: Multi-user scenarios
- **Memory Usage**: Resource consumption monitoring
- **Database Performance**: Query optimization

### Load Tests (`test_load_locust.py`)
- **User Simulation**: Realistic user behavior patterns
- **Stress Testing**: High concurrent load scenarios
- **Different User Types**: Regular users, admin users, stress users
- **Performance Benchmarks**: Response time percentiles

## 📊 Test Coverage

Current coverage: **28%** (target: 70%+)

### Coverage by Module:
- `backend/api/schemas.py`: 100%
- `backend/config.py`: 100%
- `backend/tests/backend/test_simple.py`: 88%
- `backend/models/user.py`: 69%
- `backend/models/conversation.py`: 66%
- `backend/main.py`: 56%

### Generate Coverage Reports:
```bash
# HTML report
pytest backend/tests/backend/ --cov=backend --cov-report=html:htmlcov

# Terminal report
pytest backend/tests/backend/ --cov=backend --cov-report=term-missing

# XML report (CI/CD)
pytest backend/tests/backend/ --cov=backend --cov-report=xml:coverage.xml
```

## 🏗 Test Infrastructure

### Fixtures (conftest.py)
- **Environment Setup**: Test database, Redis, environment variables
- **Service Mocking**: OpenAI, Qdrant, Mem0, Redis mocks
- **Test Data**: Sample users, messages, company data
- **Async Support**: Event loop, async clients

### Configuration (pytest.ini)
- **Test Discovery**: Automatic test file detection
- **Markers**: Custom test categories (unit, integration, performance)
- **Coverage**: Built-in coverage reporting
- **Async Mode**: Automatic async test handling

## 🚦 Load Testing with Locust

### Basic Load Test
```bash
# Start Locust with web UI
locust -f backend/tests/backend/test_load_locust.py --host=http://localhost:8000

# Open http://localhost:8089 to configure and run tests
```

### Headless Load Test
```bash
# Quick load test (10 users, 30 seconds)
locust -f backend/tests/backend/test_load_locust.py --host=http://localhost:8000 --headless -u 10 -r 2 -t 30s
```

### Load Test Scenarios:
- **DextrendsUser**: Realistic user behavior (chat, auth, profile)
- **AdminUser**: Admin-focused operations
- **StressTestUser**: Aggressive testing patterns
- **BenchmarkUser**: Performance measurement focused

## 🔧 Environment Setup

### Required Environment Variables:
```bash
ENVIRONMENT=test
DATABASE_URL=sqlite:///test.db
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=test-secret-key-for-testing-only
OPENAI_API_KEY=test-key
MEM0_API_KEY=test-mem0-key
QDRANT_URL=http://localhost:6333
```

### Services Required:
- **PostgreSQL/SQLite**: Database
- **Redis**: Caching and sessions
- **Qdrant**: Vector database (for integration tests)

## 📈 Performance Benchmarks

### Expected Performance Metrics:
- **Health Endpoint**: < 100ms (95th percentile)
- **RAG Queries**: < 5s (95th percentile)
- **Authentication**: < 1.5s (95th percentile)
- **Database Queries**: < 100ms (mean)

### Load Testing Targets:
- **Concurrent Users**: 50+ users
- **Error Rate**: < 5% under normal load
- **Response Time**: Stable under 2s for 95% of requests

## 🐛 Debugging Tests

### Verbose Output:
```bash
pytest backend/tests/backend/ -vvv --tb=long -s
```

### Debug Mode:
```bash
pytest backend/tests/backend/ --pdb
```

### Single Test:
```bash
pytest backend/tests/backend/test_simple.py::TestBasicFunctionality::test_python_version -vvv
```

## 🔄 Continuous Integration

### CI Command:
```bash
pytest backend/tests/backend/ -v --tb=short --cov=backend --cov-report=xml:coverage.xml --junitxml=junit.xml
```

### Quality Gates:
- All tests must pass
- Coverage >= 70%
- No critical security issues
- Performance benchmarks met

## 📝 Adding New Tests

### Unit Test Example:
```python
@pytest.mark.unit
async def test_my_service(my_service_fixture):
    result = await my_service_fixture.method("input")
    assert result == "expected_output"
```

### Integration Test Example:
```python
@pytest.mark.integration
@pytest.mark.api
async def test_api_endpoint(async_client, auth_headers):
    response = await async_client.post("/api/endpoint", 
        json={"data": "test"}, 
        headers=auth_headers
    )
    assert response.status_code == 200
```

### Performance Test Example:
```python
@pytest.mark.performance
async def test_endpoint_performance(perf_suite):
    results = await perf_suite.concurrent_requests("GET", "/endpoint", 100)
    analysis = perf_suite.analyze_performance(results, "Test Name")
    assert analysis["error_rate"] < 5.0
```

## 🏆 Test Quality Standards

### Requirements:
1. **Test Coverage**: Minimum 70% line coverage
2. **Test Isolation**: Each test must be independent
3. **Async Support**: Proper async/await usage
4. **Mocking**: External services must be mocked
5. **Documentation**: Clear test descriptions and assertions
6. **Performance**: Tests should complete in reasonable time

### Best Practices:
- Use descriptive test names
- Test both success and error cases
- Mock external dependencies
- Use appropriate fixtures
- Follow AAA pattern (Arrange, Act, Assert)
- Clean up resources after tests

## 🚨 Troubleshooting

### Common Issues:

#### Import Errors:
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH=/home/hoangdh/bluebelt_assignment:$PYTHONPATH
```

#### Async Test Issues:
```bash
# Use pytest-asyncio markers
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

#### Coverage Issues:
```bash
# Run with coverage debug
pytest --cov=backend --cov-report=term-missing --cov-config=.coveragerc
```

#### Database Issues:
```bash
# Use test database
export DATABASE_URL=sqlite:///test.db
```

## 📚 Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Locust Documentation](https://docs.locust.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Status**: ✅ **COMPREHENSIVE TESTING SUITE SUCCESSFULLY IMPLEMENTED**

- **Test Infrastructure**: Complete
- **Unit Tests**: Implemented
- **Integration Tests**: Implemented  
- **Performance Tests**: Implemented
- **Load Tests**: Implemented
- **Coverage Reporting**: Configured
- **Documentation**: Complete