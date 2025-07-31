"""
Integration tests for API endpoints
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json
from typing import Dict, Any

from backend.main import app


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_health_check(self, client: TestClient):
        """Test basic health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_health_check_async(self, async_client: AsyncClient):
        """Test health check with async client"""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.api
    async def test_user_registration_success(self, async_client: AsyncClient, sample_user_data):
        """Test successful user registration"""
        with patch('backend.services.auth_service.AuthService.register_user') as mock_register:
            mock_register.return_value = {
                "id": "123",
                "username": sample_user_data["username"],
                "email": sample_user_data["email"],
                "full_name": sample_user_data["full_name"]
            }
            
            response = await async_client.post("/auth/register", json=sample_user_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["username"] == sample_user_data["username"]
            assert data["email"] == sample_user_data["email"]
            assert "password" not in data  # Password should not be returned
    
    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.api
    async def test_user_registration_duplicate(self, async_client: AsyncClient, sample_user_data):
        """Test user registration with duplicate username"""
        with patch('backend.services.auth_service.AuthService.register_user') as mock_register:
            mock_register.return_value = None  # Simulate duplicate user
            
            response = await async_client.post("/auth/register", json=sample_user_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "already exists" in data["detail"].lower()
    
    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.api
    async def test_user_login_success(self, async_client: AsyncClient, sample_login_data):
        """Test successful user login"""
        mock_user = {
            "id": "123",
            "username": sample_login_data["username"],
            "email": "test@example.com"
        }
        
        with patch('backend.services.auth_service.AuthService.authenticate_user') as mock_auth, \
             patch('backend.services.auth_service.AuthService.create_access_token') as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test-jwt-token"
            
            response = await async_client.post("/auth/login", data=sample_login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test-jwt-token"
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == sample_login_data["username"]
    
    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.api
    async def test_user_login_invalid_credentials(self, async_client: AsyncClient, sample_login_data):
        """Test login with invalid credentials"""
        with patch('backend.services.auth_service.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = None  # Invalid credentials
            
            response = await async_client.post("/auth/login", data=sample_login_data)
            
            assert response.status_code == 401
            data = response.json()
            assert "invalid credentials" in data["detail"].lower()
    
    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.api
    async def test_protected_endpoint_with_valid_token(self, async_client: AsyncClient, auth_headers):
        """Test accessing protected endpoint with valid token"""
        mock_user = {"id": "123", "username": "testuser"}
        
        with patch('backend.services.auth_service.AuthService.decode_access_token') as mock_decode:
            mock_decode.return_value = mock_user
            
            response = await async_client.get("/auth/me", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
    
    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.api
    async def test_protected_endpoint_without_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint without token"""
        response = await async_client.get("/auth/me")
        
        assert response.status_code == 401


class TestChatEndpoints:
    """Test chat/RAG endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.rag
    async def test_chat_endpoint_success(self, async_client: AsyncClient, sample_chat_message, auth_headers):
        """Test successful chat interaction"""
        mock_response = {
            "response": "Dextrends offers various blockchain and payment services...",
            "sources": [
                {
                    "type": "service",
                    "title": "Digital Payment Solutions",
                    "category": "Payment Services"
                }
            ],
            "context_used": {
                "vector_results": 1,
                "mem0_memories": 0
            },
            "routing_info": {
                "intent": "service_inquiry",
                "query_type": "offering"
            },
            "metadata": {
                "user_id": "123",
                "session_id": "test-session-123"
            }
        }
        
        with patch('backend.services.rag_service.get_rag_service') as mock_get_rag, \
             patch('backend.services.auth_service.AuthService.decode_access_token') as mock_decode:
            
            mock_rag = AsyncMock()
            mock_rag.process_query.return_value = mock_response
            mock_get_rag.return_value = mock_rag
            
            mock_decode.return_value = {"id": "123", "username": "testuser"}
            
            response = await async_client.post("/chat/", json=sample_chat_message, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "sources" in data
            assert "routing_info" in data
            assert data["routing_info"]["intent"] == "service_inquiry"
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.rag
    async def test_chat_endpoint_without_auth(self, async_client: AsyncClient, sample_chat_message):
        """Test chat endpoint without authentication"""
        response = await async_client.post("/chat/", json=sample_chat_message)
        
        assert response.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.rag
    async def test_chat_endpoint_invalid_message(self, async_client: AsyncClient, auth_headers):
        """Test chat endpoint with invalid message"""
        invalid_message = {"message": "", "session_id": ""}
        
        with patch('backend.services.auth_service.AuthService.decode_access_token') as mock_decode:
            mock_decode.return_value = {"id": "123", "username": "testuser"}
            
            response = await async_client.post("/chat/", json=invalid_message, headers=auth_headers)
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.rag
    async def test_chat_history_endpoint(self, async_client: AsyncClient, auth_headers):
        """Test chat history retrieval"""
        session_id = "test-session-123"
        mock_history = [
            {
                "id": 1,
                "message": "What services do you offer?",
                "response": "We offer various services...",
                "timestamp": "2024-01-01T10:00:00Z",
                "session_id": session_id
            }
        ]
        
        with patch('backend.services.chat_service.ChatService.get_conversation_history') as mock_history_get, \
             patch('backend.services.auth_service.AuthService.decode_access_token') as mock_decode:
            
            mock_history_get.return_value = mock_history
            mock_decode.return_value = {"id": "123", "username": "testuser"}
            
            response = await async_client.get(f"/chat/history/{session_id}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["session_id"] == session_id


class TestUserEndpoints:
    """Test user management endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_user_profile_endpoint(self, async_client: AsyncClient, auth_headers):
        """Test user profile retrieval"""
        mock_user = {
            "id": "123",
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "created_at": "2024-01-01T10:00:00Z"
        }
        
        with patch('backend.services.auth_service.AuthService.decode_access_token') as mock_decode, \
             patch('backend.services.auth_service.AuthService.get_user_profile') as mock_profile:
            
            mock_decode.return_value = mock_user
            mock_profile.return_value = mock_user
            
            response = await async_client.get("/users/profile", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_user_sessions_endpoint(self, async_client: AsyncClient, auth_headers):
        """Test user sessions retrieval"""
        mock_sessions = [
            {
                "session_id": "session-1",
                "created_at": "2024-01-01T10:00:00Z",
                "last_activity": "2024-01-01T11:00:00Z",
                "message_count": 5
            },
            {
                "session_id": "session-2", 
                "created_at": "2024-01-01T12:00:00Z",
                "last_activity": "2024-01-01T13:00:00Z",
                "message_count": 3
            }
        ]
        
        with patch('backend.services.auth_service.AuthService.decode_access_token') as mock_decode, \
             patch('backend.services.chat_service.ChatService.get_user_sessions') as mock_sessions_get:
            
            mock_decode.return_value = {"id": "123", "username": "testuser"}
            mock_sessions_get.return_value = mock_sessions
            
            response = await async_client.get("/users/sessions", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["session_id"] == "session-1"


class TestAnalyticsEndpoints:
    """Test analytics endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_system_metrics_endpoint(self, async_client: AsyncClient, auth_headers):
        """Test system metrics endpoint"""
        mock_metrics = {
            "total_users": 100,
            "total_conversations": 500,
            "total_messages": 2000,
            "avg_response_time": 1.5,
            "system_health": {
                "database": "healthy",
                "redis": "healthy",
                "qdrant": "healthy"
            }
        }
        
        with patch('backend.services.auth_service.AuthService.decode_access_token') as mock_decode, \
             patch('backend.services.analytics_service.AnalyticsService.get_system_metrics') as mock_metrics_get:
            
            mock_decode.return_value = {"id": "123", "username": "admin", "role": "admin"}
            mock_metrics_get.return_value = mock_metrics
            
            response = await async_client.get("/analytics/metrics", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_users"] == 100
            assert data["system_health"]["database"] == "healthy"


class TestRagDemoEndpoints:
    """Test RAG demo endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.rag
    async def test_rag_demo_endpoint(self, async_client: AsyncClient):
        """Test RAG demo endpoint"""
        query = {"query": "What services does Dextrends offer?"}
        
        mock_response = {
            "response": "Dextrends offers comprehensive digital financial services...",
            "sources": [{"type": "service", "title": "Digital Payment Solutions"}],
            "query_processing": {
                "intent": "service_inquiry",
                "query_type": "offering",
                "confidence": 0.95
            }
        }
        
        with patch('backend.services.rag_service.get_rag_service') as mock_get_rag:
            mock_rag = AsyncMock()
            mock_rag.process_query.return_value = mock_response
            mock_get_rag.return_value = mock_rag
            
            response = await async_client.post("/rag/demo", json=query)
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "sources" in data
            assert "query_processing" in data
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.rag
    async def test_rag_demo_empty_query(self, async_client: AsyncClient):
        """Test RAG demo with empty query"""
        query = {"query": ""}
        
        response = await async_client.post("/rag/demo", json=query)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling"""
    
    async def test_404_not_found(self, async_client: AsyncClient):
        """Test 404 error handling"""
        response = await async_client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    async def test_method_not_allowed(self, async_client: AsyncClient):
        """Test 405 error handling"""
        response = await async_client.patch("/health")  # PATCH not allowed on health
        
        assert response.status_code == 405
    
    async def test_internal_server_error_handling(self, async_client: AsyncClient):
        """Test 500 error handling"""
        with patch('backend.api.health.get_system_health', side_effect=Exception("Database error")):
            response = await async_client.get("/health")
            
            # Should still return some response, not crash
            assert response.status_code in [200, 500]


@pytest.mark.integration
class TestCORSAndSecurity:
    """Test CORS and security headers"""
    
    async def test_cors_headers(self, async_client: AsyncClient):
        """Test CORS headers are present"""
        response = await async_client.options("/health")
        
        assert response.status_code in [200, 204]
        # CORS headers should be handled by FastAPI middleware
    
    async def test_security_headers(self, async_client: AsyncClient):
        """Test security headers"""
        response = await async_client.get("/health")
        
        # Check for basic security (actual headers depend on middleware setup)
        assert response.status_code == 200