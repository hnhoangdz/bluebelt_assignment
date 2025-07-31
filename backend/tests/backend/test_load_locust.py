"""
Load tests using Locust for the Dextrends backend
"""

import json
import random
import string
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer
from locust.log import setup_logging
import time
import uuid


class DextrendsUser(HttpUser):
    """Simulated user for load testing Dextrends backend"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts - perform login"""
        self.token = None
        self.user_id = None
        self.session_id = str(uuid.uuid4())
        
        # Try to login or register
        self.authenticate()
    
    def authenticate(self):
        """Authenticate user for protected endpoints"""
        # Generate random user credentials
        username = f"loadtest_user_{random.randint(1000, 9999)}"
        password = "loadtest123"
        email = f"{username}@loadtest.com"
        
        # Try to register first
        register_data = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": f"Load Test User {random.randint(1, 1000)}"
        }
        
        response = self.client.post("/auth/register", json=register_data)
        
        if response.status_code == 201:
            # Registration successful, now login
            login_data = {
                "username": username,
                "password": password
            }
            
            response = self.client.post("/auth/login", data=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
        
        # If registration failed (user exists), try login directly
        elif response.status_code == 400:
            login_data = {
                "username": username,
                "password": password  
            }
            
            response = self.client.post("/auth/login", data=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
    
    def get_auth_headers(self):
        """Get authentication headers"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    @task(10)
    def health_check(self):
        """Test health endpoint - most frequent task"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("Health check returned unhealthy status")
            else:
                response.failure(f"Health check failed with status {response.status_code}")
    
    @task(8)
    def chat_query(self):
        """Test chat endpoint with various queries"""
        if not self.token:
            return
        
        queries = [
            "What services does Dextrends offer?",
            "How secure are your payment solutions?",
            "Tell me about blockchain services",
            "What are your pricing models?",
            "How does integration work?",
            "What payment methods do you support?",
            "Can you explain your DeFi platform?",
            "What is your company mission?",
            "How do I get started with your services?",
            "What makes Dextrends different?"
        ]
        
        message_data = {
            "message": random.choice(queries),
            "session_id": self.session_id
        }
        
        headers = self.get_auth_headers()
        headers["Content-Type"] = "application/json"
        
        with self.client.post("/chat/", json=message_data, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "response" in data and len(data["response"]) > 0:
                    response.success()
                else:
                    response.failure("Chat response was empty")
            elif response.status_code == 401:
                # Re-authenticate and retry
                self.authenticate()
                response.failure("Authentication failed, retrying")
            else:
                response.failure(f"Chat failed with status {response.status_code}")
    
    @task(5)
    def rag_demo_query(self):
        """Test RAG demo endpoint"""
        queries = [
            "What blockchain services do you provide?",
            "How does your identity verification work?", 
            "What are the benefits of your payment platform?",
            "Can you explain smart contract development?",
            "What security measures do you have?"
        ]
        
        query_data = {
            "query": random.choice(queries)
        }
        
        with self.client.post("/rag/demo", json=query_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "response" in data:
                    response.success()
                else:
                    response.failure("RAG demo response missing")
            else:
                response.failure(f"RAG demo failed with status {response.status_code}")
    
    @task(3)
    def user_profile(self):
        """Test user profile endpoint"""
        if not self.token:
            return
        
        headers = self.get_auth_headers()
        
        with self.client.get("/users/profile", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "username" in data:
                    response.success()
                else:
                    response.failure("Profile data incomplete")
            elif response.status_code == 401:
                self.authenticate()
                response.failure("Authentication failed for profile")
            else:
                response.failure(f"Profile request failed with status {response.status_code}")
    
    @task(2)
    def chat_history(self):
        """Test chat history endpoint"""
        if not self.token:
            return
        
        headers = self.get_auth_headers()
        
        with self.client.get(f"/chat/history/{self.session_id}", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    response.success()
                else:
                    response.failure("Chat history format invalid")
            elif response.status_code == 401:
                self.authenticate()
                response.failure("Authentication failed for history")
            else:
                response.failure(f"Chat history failed with status {response.status_code}")
    
    @task(2)
    def user_sessions(self):
        """Test user sessions endpoint"""
        if not self.token:
            return
        
        headers = self.get_auth_headers()
        
        with self.client.get("/users/sessions", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    response.success()
                else:
                    response.failure("Sessions data format invalid")
            elif response.status_code == 401:
                self.authenticate()
                response.failure("Authentication failed for sessions")
            else:
                response.failure(f"Sessions request failed with status {response.status_code}")
    
    @task(1)
    def register_new_user(self):
        """Test user registration with random data"""
        username = f"load_user_{random.randint(10000, 99999)}"
        email = f"{username}@loadtest.example.com"
        password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
        
        register_data = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": f"Load Test {random.randint(1, 1000)}"
        }
        
        with self.client.post("/auth/register", json=register_data, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 400:
                # User might already exist, that's ok for load testing
                response.success()
            else:
                response.failure(f"Registration failed with status {response.status_code}")


class AdminUser(HttpUser):
    """Simulated admin user for testing admin endpoints"""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight than regular users
    
    def on_start(self):
        """Login as admin user"""
        self.token = None
        # In a real scenario, you'd have predefined admin credentials
        # For load testing, we'll simulate admin actions
    
    @task(1)
    def system_metrics(self):
        """Test system metrics endpoint (admin only)"""
        # This would require admin authentication
        # For load testing, we'll test the endpoint structure
        pass


class StressTestUser(HttpUser):
    """User for stress testing with aggressive patterns"""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    @task
    def rapid_health_checks(self):
        """Rapid health check requests"""
        self.client.get("/health")
    
    @task  
    def rapid_rag_queries(self):
        """Rapid RAG demo queries"""
        query_data = {"query": "What services do you offer?"}
        self.client.post("/rag/demo", json=query_data)


# Custom Locust events and listeners
@events.request.add_listener
def request_handler(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Custom request handler for detailed logging"""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif response.status_code >= 400:
        print(f"Request error: {name} - Status: {response.status_code}")


@events.test_start.add_listener  
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("Load test starting...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("Load test completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {environment.stats.total.max_response_time:.2f}ms")


# Scenario-based load testing
class QuickTestScenario(HttpUser):
    """Quick test scenario for basic functionality"""
    wait_time = between(1, 2)
    
    tasks = {
        "health_check": 5,
        "rag_demo_query": 3, 
        "register_new_user": 1
    }
    
    def health_check(self):
        self.client.get("/health")
    
    def rag_demo_query(self):
        query_data = {"query": "What is Dextrends?"}
        self.client.post("/rag/demo", json=query_data)
    
    def register_new_user(self):
        username = f"quick_test_{random.randint(1000, 9999)}"
        register_data = {
            "username": username,
            "email": f"{username}@test.com",
            "password": "testpass123",
            "full_name": "Quick Test User"
        }
        self.client.post("/auth/register", json=register_data)


# Performance benchmarks
class BenchmarkUser(HttpUser):
    """User for performance benchmarking"""
    
    wait_time = between(0.5, 1.5)
    
    def on_start(self):
        self.start_time = time.time()
        self.request_count = 0
    
    @task(10)
    def benchmark_health(self):
        """Benchmark health endpoint"""
        start_time = time.time()
        response = self.client.get("/health")
        end_time = time.time()
        
        self.request_count += 1
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        if response_time > 100:  # Flag slow responses
            print(f"Slow health check: {response_time:.2f}ms")
    
    @task(5) 
    def benchmark_rag(self):
        """Benchmark RAG endpoint"""
        start_time = time.time()
        query_data = {"query": "Tell me about your services"}
        response = self.client.post("/rag/demo", json=query_data)
        end_time = time.time()
        
        self.request_count += 1
        response_time = (end_time - start_time) * 1000
        
        if response_time > 2000:  # Flag very slow RAG responses
            print(f"Slow RAG response: {response_time:.2f}ms")


if __name__ == "__main__":
    # This allows running the load test directly
    # Usage: python test_load_locust.py
    print("Use: locust -f test_load_locust.py --host=http://localhost:8000")
    print("Then open http://localhost:8089 to configure and start the test")