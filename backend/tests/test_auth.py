"""
Tests for authentication functionality
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..main import app
from ..core.database import get_db
from ..models.base import Base


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Test client fixture"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    Base.metadata.drop_all(bind=engine)


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",
            "first_name": "Test",
            "last_name": "User"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User registered successfully"
    assert "user_id" in data["data"]


def test_login_user(client):
    """Test user login"""
    # First register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",
            "first_name": "Test",
            "last_name": "User"
        }
    )
    
    # Then login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "securepassword123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_get_current_user(client):
    """Test getting current user info"""
    # Register and login
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",
            "first_name": "Test",
            "last_name": "User"
        }
    )
    
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "securepassword123"
        }
    )
    
    token = login_response.json()["access_token"]
    
    # Get current user
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


def test_invalid_token(client):
    """Test accessing protected endpoint with invalid token"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401 