"""
Simple tests to verify testing infrastructure works
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path for imports
sys.path.insert(0, './bluebelt_assignment')
sys.path.insert(0, './bluebelt_assignment/backend')


class TestBasicFunctionality:
    """Basic functionality tests"""
    
    def test_python_version(self):
        """Test Python version is acceptable"""
        version = sys.version_info
        assert version.major == 3
        assert version.minor >= 8  # Python 3.8+
    
    def test_imports_work(self):
        """Test that basic imports work"""
        # Test that we can import our modules
        try:
            from backend.config import settings
            assert settings is not None
        except ImportError as e:
            pytest.fail(f"Failed to import settings: {e}")
    
    def test_environment_variables(self):
        """Test environment variables are set for testing"""
        # These should be set by our test runner
        test_vars = ['SECRET_KEY', 'OPENAI_API_KEY']
        for var in test_vars:
            assert os.environ.get(var) is not None, f"Environment variable {var} not set"
    
    @pytest.mark.unit
    def test_basic_math(self):
        """Test basic math operations"""
        assert 1 + 1 == 2
        assert 2 * 3 == 6
        assert 10 / 2 == 5.0
    
    @pytest.mark.unit
    def test_string_operations(self):
        """Test string operations"""
        test_string = "Hello, World!"
        assert len(test_string) == 13
        assert test_string.lower() == "hello, world!"
        assert "Hello" in test_string


class TestAsyncFunctionality:
    """Test async functionality"""
    
    @pytest.mark.asyncio
    async def test_async_basic(self):
        """Test basic async functionality"""
        async def async_function():
            await asyncio.sleep(0.01)  # Very short sleep
            return "async_result"
        
        result = await async_function()
        assert result == "async_result"
    
    @pytest.mark.asyncio
    async def test_async_with_mock(self):
        """Test async with mocking"""
        async def mock_async_function():
            return "mocked_result"
        
        with patch('asyncio.sleep', return_value=None):
            result = await mock_async_function()
            assert result == "mocked_result"


class TestMockingFunctionality:
    """Test mocking functionality"""
    
    def test_basic_mock(self):
        """Test basic mocking"""
        mock_obj = MagicMock()
        mock_obj.method.return_value = "mocked_value"
        
        result = mock_obj.method()
        assert result == "mocked_value"
        mock_obj.method.assert_called_once()
    
    def test_patch_decorator(self):
        """Test patch decorator"""
        # Test patching a custom function instead of builtin
        def custom_function(x):
            return x * 2
        
        with patch(__name__ + '.custom_function') as mock_func:
            mock_func.return_value = 42
            
            result = mock_func("test")
            assert result == 42
            mock_func.assert_called_once_with("test")


class TestServiceMocking:
    """Test mocking of our services"""
    
    def test_auth_service_mock(self):
        """Test AuthService can be mocked"""
        with patch('backend.services.auth_service.AuthService') as MockAuthService:
            mock_instance = MockAuthService.return_value
            mock_instance.hash_password.return_value = "hashed_password"
            
            # This simulates using the mocked service  
            service = MockAuthService()
            result = service.hash_password("test_password")
            
            assert result == "hashed_password"
            mock_instance.hash_password.assert_called_once_with("test_password")
    
    @pytest.mark.asyncio
    async def test_async_service_mock(self):
        """Test async service mocking"""
        from unittest.mock import AsyncMock
        
        mock_service = AsyncMock()
        mock_service.process_query.return_value = {"response": "test_response"}
        
        result = await mock_service.process_query("test_query")
        assert result == {"response": "test_response"}
        mock_service.process_query.assert_called_once_with("test_query")


@pytest.mark.integration
class TestIntegrationBasics:
    """Basic integration tests"""
    
    def test_config_loading(self):
        """Test configuration loading"""
        try:
            from backend.config import settings
            
            # Test that config values are loaded
            assert hasattr(settings, 'app_name')
            assert hasattr(settings, 'secret_key')
            assert hasattr(settings, 'openai_api_key')
            
        except Exception as e:
            pytest.fail(f"Config loading failed: {e}")
    
    def test_fastapi_import(self):
        """Test FastAPI can be imported"""
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            
            app = FastAPI()
            client = TestClient(app)
            
            assert app is not None
            assert client is not None
            
        except ImportError as e:
            pytest.fail(f"FastAPI import failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])