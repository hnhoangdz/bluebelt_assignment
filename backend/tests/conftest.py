"""
Test configuration and fixtures for the Dextrends backend
"""

import asyncio
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from fastapi import FastAPI
from fastapi.testclient import TestClient
import tempfile
import json
from typing import AsyncGenerator, Generator, Dict, Any

# Import application components
import sys
sys.path.insert(0, '/home/hoangdh/bluebelt_assignment')
sys.path.insert(0, '/home/hoangdh/bluebelt_assignment/backend')

from backend.main import app
from backend.config import settings
from backend.services.auth_service import AuthService
from backend.services.rag_service import RAGService
from backend.services.embedding_service import EmbeddingService
from backend.services.query_processor import QueryProcessor
from backend.core.qdrant_client import QdrantService

# Test environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ.update({
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/1",  # Use different DB for tests
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "OPENAI_API_KEY": "test-key",
        "MEM0_API_KEY": "test-mem0-key",
        "QDRANT_URL": "http://localhost:6333",
    })
    yield
    # Cleanup after tests
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_app() -> FastAPI:
    """Get test FastAPI application"""
    return app

@pytest.fixture
def client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client"""
    with TestClient(test_app) as test_client:
        yield test_client

@pytest_asyncio.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client"""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac

# Mock fixtures for external services
@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    with patch('openai.OpenAI') as mock:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        
        # Mock embeddings
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock()]
        mock_embedding_response.data[0].embedding = [0.1] * 1536
        
        mock_client.chat.completions.create.return_value = mock_response
        mock_client.embeddings.create.return_value = mock_embedding_response
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client"""
    with patch('backend.core.qdrant_client.QdrantClient') as mock:
        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = []
        mock_client.search.return_value = []
        mock_client.upsert.return_value = True
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_mem0():
    """Mock Mem0 client"""
    with patch('mem0.MemoryClient') as mock:
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_client.add.return_value = {"id": "test-memory-id"}
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.Redis') as mock:
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.delete.return_value = True
        mock.return_value = mock_client
        yield mock_client

# Service fixtures
@pytest_asyncio.fixture
async def auth_service(mock_redis):
    """Create AuthService instance for testing"""
    service = AuthService()
    yield service

@pytest_asyncio.fixture
async def rag_service(mock_openai, mock_qdrant, mock_mem0):
    """Create RAGService instance for testing"""
    service = RAGService()
    yield service

@pytest_asyncio.fixture
async def embedding_service(mock_openai, mock_qdrant):
    """Create EmbeddingService instance for testing"""
    service = EmbeddingService()
    yield service

@pytest_asyncio.fixture
async def query_processor(mock_openai):
    """Create QueryProcessor instance for testing"""
    service = QueryProcessor()
    yield service

# Test data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }

@pytest.fixture
def sample_login_data():
    """Sample login data for testing"""
    return {
        "username": "testuser",
        "password": "testpassword123"
    }

@pytest.fixture
def sample_chat_message():
    """Sample chat message for testing"""
    return {
        "message": "What services does Dextrends offer?",
        "session_id": "test-session-123"
    }

@pytest.fixture
def sample_company_data():
    """Sample company offerings data"""
    return {
        "company_info": {
            "name": "Dextrends",
            "description": "Leading technology company",
            "mission": "Empowering businesses"
        },
        "services": [
            {
                "id": "service_001",
                "title": "Digital Payment Solutions",
                "category": "Payment Services",
                "description": "Comprehensive digital payment platform",
                "features": ["Multi-currency support", "Real-time settlement"],
                "pricing": "1.5% per transaction"
            }
        ]
    }

@pytest.fixture
def sample_faq_data():
    """Sample FAQ data"""
    return [
        {
            "id": "faq_001",
            "category": "General",
            "question": "What is Dextrends?",
            "answer": "Dextrends is a leading technology company",
            "keywords": ["company", "services", "about"]
        }
    ]

@pytest.fixture
def auth_headers():
    """Generate auth headers for testing"""
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json"
    }

# Database fixtures
@pytest_asyncio.fixture
async def test_db():
    """Create test database"""
    # Use in-memory SQLite for tests
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_url = f"sqlite:///{tmp_file.name}"
        yield test_db_url
        # Cleanup
        os.unlink(tmp_file.name)

# Utility fixtures
@pytest.fixture
def temp_file():
    """Create temporary file for testing"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
        yield tmp_file.name
        os.unlink(tmp_file.name)

@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    test_settings = {
        "app_name": "Dextrends AI Chatbot Test",
        "environment": "test",
        "debug": True,
        "secret_key": "test-secret-key",
        "openai_api_key": "test-openai-key",
        "openai_model": "gpt-4.1-nano",
        "database_url": "sqlite:///test.db",
        "redis_url": "redis://localhost:6379/1"
    }
    
    with patch.object(settings, '__dict__', test_settings):
        yield test_settings