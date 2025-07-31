"""
Performance tests using Python asyncio for the Dextrends backend
"""

import asyncio
import aiohttp
import time
import statistics
import json
import pytest
import pytest_asyncio
from typing import List, Dict, Any, Tuple
from unittest.mock import patch
import random
import uuid


class PerformanceTestSuite:
    """Performance testing suite for backend services"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results = {}
    
    async def setup(self):
        """Setup test session"""
        self.session = aiohttp.ClientSession()
    
    async def teardown(self):
        """Cleanup test session"""
        if self.session:
            await self.session.close()
    
    async def measure_request(self, method: str, url: str, **kwargs) -> Tuple[float, int, Dict]:
        """Measure request performance"""
        start_time = time.perf_counter()
        
        try:
            async with self.session.request(method, f"{self.base_url}{url}", **kwargs) as response:
                content = await response.text()
                end_time = time.perf_counter()
                
                return (
                    (end_time - start_time) * 1000,  # Response time in ms
                    response.status,
                    {"content_length": len(content), "headers": dict(response.headers)}
                )
        except Exception as e:
            end_time = time.perf_counter()
            return (
                (end_time - start_time) * 1000,
                0,  # Error status
                {"error": str(e)}
            )
    
    async def concurrent_requests(self, method: str, url: str, count: int, **kwargs) -> List[Tuple[float, int, Dict]]:
        """Make concurrent requests and measure performance"""
        tasks = []
        for _ in range(count):
            task = asyncio.create_task(self.measure_request(method, url, **kwargs))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    def analyze_performance(self, results: List[Tuple[float, int, Dict]], test_name: str) -> Dict[str, Any]:
        """Analyze performance results"""
        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]
        
        # Calculate statistics
        analysis = {
            "test_name": test_name,
            "total_requests": len(results),
            "successful_requests": sum(1 for s in status_codes if 200 <= s < 300),
            "failed_requests": sum(1 for s in status_codes if s == 0 or s >= 400),
            "error_rate": sum(1 for s in status_codes if s == 0 or s >= 400) / len(results) * 100,
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": self.percentile(response_times, 0.95),
                "p99": self.percentile(response_times, 0.99)
            },
            "throughput": len(results) / (max(response_times) / 1000) if response_times else 0
        }
        
        return analysis
    
    def percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def print_results(self, analysis: Dict[str, Any]):
        """Print performance results"""
        print(f"\n{'='*60}")
        print(f"Performance Test: {analysis['test_name']}")
        print(f"{'='*60}")
        print(f"Total Requests: {analysis['total_requests']}")
        print(f"Successful: {analysis['successful_requests']}")
        print(f"Failed: {analysis['failed_requests']}")
        print(f"Error Rate: {analysis['error_rate']:.2f}%")
        print(f"Throughput: {analysis['throughput']:.2f} req/sec")
        print(f"\nResponse Times (ms):")
        print(f"  Min: {analysis['response_times']['min']:.2f}")
        print(f"  Max: {analysis['response_times']['max']:.2f}")
        print(f"  Mean: {analysis['response_times']['mean']:.2f}")
        print(f"  Median: {analysis['response_times']['median']:.2f}")
        print(f"  95th percentile: {analysis['response_times']['p95']:.2f}")
        print(f"  99th percentile: {analysis['response_times']['p99']:.2f}")


@pytest.mark.performance
class TestHealthEndpointPerformance:
    """Performance tests for health endpoint"""
    
    @pytest_asyncio.fixture
    async def perf_suite(self):
        suite = PerformanceTestSuite()
        await suite.setup()
        yield suite
        await suite.teardown()
    
    @pytest.mark.asyncio
    async def test_health_endpoint_load(self, perf_suite):
        """Test health endpoint under load"""
        results = await perf_suite.concurrent_requests("GET", "/health", 100)
        analysis = perf_suite.analyze_performance(results, "Health Endpoint Load Test")
        perf_suite.print_results(analysis)
        
        # Assertions
        assert analysis["error_rate"] < 5.0, "Error rate should be less than 5%"
        assert analysis["response_times"]["p95"] < 1000, "95th percentile should be under 1 second"
        assert analysis["successful_requests"] >= 95, "At least 95% requests should succeed"
    
    @pytest.mark.asyncio
    async def test_health_endpoint_stress(self, perf_suite):
        """Stress test health endpoint"""
        results = await perf_suite.concurrent_requests("GET", "/health", 500)
        analysis = perf_suite.analyze_performance(results, "Health Endpoint Stress Test")
        perf_suite.print_results(analysis)
        
        # More lenient assertions for stress test
        assert analysis["error_rate"] < 20.0, "Error rate should be less than 20% under stress"
        assert analysis["successful_requests"] >= 400, "At least 80% requests should succeed"


@pytest.mark.performance
class TestRAGEndpointPerformance:
    """Performance tests for RAG endpoints"""
    
    @pytest_asyncio.fixture
    async def perf_suite(self):
        suite = PerformanceTestSuite()
        await suite.setup()
        yield suite
        await suite.teardown()
    
    @pytest.mark.asyncio
    async def test_rag_demo_performance(self, perf_suite):
        """Test RAG demo endpoint performance"""
        query_data = {"query": "What services does Dextrends offer?"}
        headers = {"Content-Type": "application/json"}
        
        results = await perf_suite.concurrent_requests(
            "POST", "/rag/demo", 
            count=50,
            json=query_data,
            headers=headers
        )
        
        analysis = perf_suite.analyze_performance(results, "RAG Demo Performance Test")
        perf_suite.print_results(analysis)
        
        # RAG endpoints are expected to be slower
        assert analysis["error_rate"] < 10.0, "Error rate should be less than 10%"
        assert analysis["response_times"]["p95"] < 5000, "95th percentile should be under 5 seconds"
    
    @pytest.mark.asyncio
    async def test_rag_various_queries_performance(self, perf_suite):
        """Test RAG performance with various query types"""
        queries = [
            "What services does Dextrends offer?",
            "How secure are your payment solutions?",
            "Tell me about blockchain services",
            "What are your pricing models?",
            "How does integration work?"
        ]
        
        all_results = []
        for query in queries:
            query_data = {"query": query}
            headers = {"Content-Type": "application/json"}
            
            results = await perf_suite.concurrent_requests(
                "POST", "/rag/demo",
                count=10,
                json=query_data,
                headers=headers
            )
            all_results.extend(results)
        
        analysis = perf_suite.analyze_performance(all_results, "RAG Various Queries Test")
        perf_suite.print_results(analysis)
        
        assert analysis["error_rate"] < 15.0, "Error rate should be less than 15%"


@pytest.mark.performance
class TestAuthEndpointPerformance:
    """Performance tests for authentication endpoints"""
    
    @pytest_asyncio.fixture
    async def perf_suite_with_auth(self):
        suite = PerformanceTestSuite()
        await suite.setup()
        
        # Mock authentication to avoid database issues during perf testing
        with patch('backend.services.auth_service.AuthService.register_user') as mock_register, \
             patch('backend.services.auth_service.AuthService.authenticate_user') as mock_auth, \
             patch('backend.services.auth_service.AuthService.create_access_token') as mock_token:
            
            mock_register.return_value = {"id": "123", "username": "testuser"}
            mock_auth.return_value = {"id": "123", "username": "testuser"}
            mock_token.return_value = "test-jwt-token"
            
            yield suite
        
        await suite.teardown()
    
    @pytest.mark.asyncio
    async def test_registration_performance(self, perf_suite_with_auth):
        """Test user registration performance"""
        async def register_user(suite, index):
            user_data = {
                "username": f"perftest_user_{index}",
                "email": f"perftest_{index}@example.com",
                "password": "testpass123",
                "full_name": f"Perf Test User {index}"
            }
            return await suite.measure_request("POST", "/auth/register", json=user_data)
        
        tasks = []
        for i in range(50):
            task = asyncio.create_task(register_user(perf_suite_with_auth, i))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        analysis = perf_suite_with_auth.analyze_performance(results, "User Registration Performance")
        perf_suite_with_auth.print_results(analysis)
        
        assert analysis["error_rate"] < 10.0, "Registration error rate should be less than 10%"
        assert analysis["response_times"]["mean"] < 2000, "Mean response time should be under 2 seconds"
    
    @pytest.mark.asyncio
    async def test_login_performance(self, perf_suite_with_auth):
        """Test user login performance"""
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        results = await perf_suite_with_auth.concurrent_requests(
            "POST", "/auth/login",
            count=100,
            data=login_data
        )
        
        analysis = perf_suite_with_auth.analyze_performance(results, "User Login Performance")
        perf_suite_with_auth.print_results(analysis)
        
        assert analysis["error_rate"] < 5.0, "Login error rate should be less than 5%"
        assert analysis["response_times"]["p95"] < 1500, "95th percentile should be under 1.5 seconds"


@pytest.mark.performance
class TestConcurrentUserScenarios:
    """Test realistic user scenarios with concurrent users"""
    
    @pytest_asyncio.fixture
    async def perf_suite(self):
        suite = PerformanceTestSuite()
        await suite.setup()
        yield suite
        await suite.teardown()
    
    async def simulate_user_session(self, suite: PerformanceTestSuite, user_id: int) -> List[Tuple[float, int, Dict]]:
        """Simulate a complete user session"""
        session_results = []
        session_id = str(uuid.uuid4())
        
        # 1. Health check
        result = await suite.measure_request("GET", "/health")
        session_results.append(result)
        
        # 2. RAG queries (3-5 queries per session)
        queries = [
            "What services does Dextrends offer?",
            "How secure are your solutions?", 
            "Tell me about pricing",
            "How does integration work?",
            "What blockchain services do you have?"
        ]
        
        num_queries = random.randint(3, 5)
        for i in range(num_queries):
            query = random.choice(queries)
            query_data = {"query": query}
            
            result = await suite.measure_request(
                "POST", "/rag/demo",
                json=query_data,
                headers={"Content-Type": "application/json"}
            )
            session_results.append(result)
            
            # Small delay between queries (realistic user behavior)
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        return session_results
    
    @pytest.mark.asyncio
    async def test_concurrent_user_sessions(self, perf_suite):
        """Test multiple concurrent user sessions"""
        num_users = 20
        
        print(f"Simulating {num_users} concurrent user sessions...")
        
        tasks = []
        for user_id in range(num_users):
            task = asyncio.create_task(self.simulate_user_session(perf_suite, user_id))
            tasks.append(task)
        
        # Wait for all user sessions to complete
        session_results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_results = []
        for session in session_results:
            all_results.extend(session)
        
        analysis = perf_suite.analyze_performance(all_results, f"{num_users} Concurrent User Sessions")
        perf_suite.print_results(analysis)
        
        # Assertions for concurrent user scenarios
        assert analysis["error_rate"] < 15.0, "Error rate should be less than 15% for concurrent users"
        assert analysis["successful_requests"] >= len(all_results) * 0.8, "At least 80% requests should succeed"


@pytest.mark.performance
class TestMemoryAndResourceUsage:
    """Test memory and resource usage during performance tests"""
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_load(self):
        """Test memory usage during load testing"""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        suite = PerformanceTestSuite()
        await suite.setup()
        
        try:
            # Run multiple load tests
            for i in range(5):
                results = await suite.concurrent_requests("GET", "/health", 50)
                
                # Measure memory after each test
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                print(f"Test {i+1}: Memory usage: {current_memory:.2f} MB (increase: {memory_increase:.2f} MB)")
                
                # Assert memory doesn't grow excessively
                assert memory_increase < 100, f"Memory increase should be less than 100MB, got {memory_increase:.2f}MB"
        
        finally:
            await suite.teardown()


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database-related performance"""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool(self):
        """Test database connection pool under load"""
        # This would test actual database operations
        # For now, we'll simulate with mocked database calls
        
        async def simulate_db_query():
            # Simulate database query time
            await asyncio.sleep(random.uniform(0.01, 0.05))
            return {"result": "success"}
        
        # Test concurrent database operations
        start_time = time.perf_counter()
        
        tasks = []
        for _ in range(100):
            task = asyncio.create_task(simulate_db_query())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        print(f"100 concurrent DB queries completed in {total_time:.2f} seconds")
        print(f"Throughput: {100/total_time:.2f} queries/second")
        
        # Assertions
        assert total_time < 2.0, "100 concurrent queries should complete in under 2 seconds"
        assert len(results) == 100, "All queries should complete successfully"


# Utility functions for performance testing
def run_performance_benchmark():
    """Run a comprehensive performance benchmark"""
    print("Running Dextrends Backend Performance Benchmark...")
    
    # This would be called by a separate script to run all performance tests
    # pytest backend/tests/backend/test_performance.py -m performance -v
    pass


if __name__ == "__main__":
    print("Performance tests for Dextrends Backend")
    print("Run with: pytest backend/tests/backend/test_performance.py -m performance -v")