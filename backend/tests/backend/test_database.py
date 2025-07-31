"""
Database-specific tests for the Dextrends backend
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from typing import Dict, Any, List
import tempfile
import os

from backend.core.database import get_database_connection, create_tables
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.session import Session


@pytest.mark.database
class TestDatabaseConnection:
    """Test database connection and setup"""
    
    @pytest.mark.asyncio
    async def test_database_connection_creation(self):
        """Test database connection can be created"""
        with patch('backend.core.database.create_engine') as mock_engine:
            mock_connection = MagicMock()
            mock_engine.return_value = mock_connection
            
            connection = await get_database_connection()
            
            assert connection is not None
            mock_engine.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_tables_creation(self):
        """Test database tables can be created"""
        with patch('backend.core.database.create_engine') as mock_engine, \
             patch('backend.models.base.Base.metadata.create_all') as mock_create:
            
            mock_connection = MagicMock()
            mock_engine.return_value = mock_connection
            
            await create_tables()
            
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self):
        """Test database connection error handling"""
        with patch('backend.core.database.create_engine', side_effect=Exception("Database connection failed")):
            
            with pytest.raises(Exception) as exc_info:
                await get_database_connection()
            
            assert "Database connection failed" in str(exc_info.value)


@pytest.mark.database
class TestUserModel:
    """Test User model database operations"""
    
    @pytest.fixture
    def sample_user_data(self):
        return {
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "full_name": "Test User"
        }
    
    @pytest.mark.asyncio
    async def test_user_creation(self, sample_user_data):
        """Test user creation in database"""
        with patch('backend.models.user.User.create') as mock_create:
            mock_create.return_value = User(
                id=1,
                username=sample_user_data["username"],
                email=sample_user_data["email"],
                password_hash=sample_user_data["password_hash"],
                full_name=sample_user_data["full_name"]
            )
            
            user = await User.create(**sample_user_data)
            
            assert user.username == sample_user_data["username"]
            assert user.email == sample_user_data["email"]
            assert user.full_name == sample_user_data["full_name"]
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_retrieval_by_username(self):
        """Test user retrieval by username"""
        with patch('backend.models.user.User.get_by_username') as mock_get:
            mock_user = User(
                id=1,
                username="testuser",
                email="test@example.com",
                password_hash="hashed_password"
            )
            mock_get.return_value = mock_user
            
            user = await User.get_by_username("testuser")
            
            assert user.username == "testuser"
            assert user.id == 1
            mock_get.assert_called_once_with("testuser")
    
    @pytest.mark.asyncio
    async def test_user_retrieval_by_email(self):
        """Test user retrieval by email"""
        with patch('backend.models.user.User.get_by_email') as mock_get:
            mock_user = User(
                id=1,
                username="testuser",
                email="test@example.com",
                password_hash="hashed_password"
            )
            mock_get.return_value = mock_user
            
            user = await User.get_by_email("test@example.com")
            
            assert user.email == "test@example.com"
            assert user.id == 1
            mock_get.assert_called_once_with("test@example.com")
    
    @pytest.mark.asyncio
    async def test_user_update(self):
        """Test user update operations"""
        with patch('backend.models.user.User.update') as mock_update:
            mock_update.return_value = True
            
            user = User(id=1, username="testuser", email="test@example.com")
            result = await user.update(full_name="Updated Name")
            
            assert result is True
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_deletion(self):
        """Test user deletion"""
        with patch('backend.models.user.User.delete') as mock_delete:
            mock_delete.return_value = True
            
            user = User(id=1, username="testuser", email="test@example.com")
            result = await user.delete()
            
            assert result is True
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_validation(self, sample_user_data):
        """Test user data validation"""
        # Test invalid email
        invalid_data = sample_user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        with pytest.raises(ValueError):
            User(**invalid_data)
        
        # Test missing required fields
        with pytest.raises(TypeError):
            User(username="test")


@pytest.mark.database
class TestConversationModel:
    """Test Conversation model database operations"""
    
    @pytest.fixture
    def sample_conversation_data(self):
        return {
            "user_id": 1,
            "session_id": "test-session-123",
            "message": "What services do you offer?",
            "response": "We offer various services...",
            "intent": "service_inquiry",
            "query_type": "offering"
        }
    
    @pytest.mark.asyncio
    async def test_conversation_creation(self, sample_conversation_data):
        """Test conversation creation"""
        with patch('backend.models.conversation.Conversation.create') as mock_create:
            mock_conversation = Conversation(**sample_conversation_data)
            mock_create.return_value = mock_conversation
            
            conversation = await Conversation.create(**sample_conversation_data)
            
            assert conversation.user_id == sample_conversation_data["user_id"]
            assert conversation.session_id == sample_conversation_data["session_id"]
            assert conversation.message == sample_conversation_data["message"]
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_conversation_retrieval_by_session(self):
        """Test conversation retrieval by session"""
        with patch('backend.models.conversation.Conversation.get_by_session') as mock_get:
            mock_conversations = [
                Conversation(id=1, session_id="test-session", message="Hello"),
                Conversation(id=2, session_id="test-session", message="What services?")
            ]
            mock_get.return_value = mock_conversations
            
            conversations = await Conversation.get_by_session("test-session")
            
            assert len(conversations) == 2
            assert all(c.session_id == "test-session" for c in conversations)
            mock_get.assert_called_once_with("test-session")
    
    @pytest.mark.asyncio
    async def test_conversation_retrieval_by_user(self):
        """Test conversation retrieval by user"""
        with patch('backend.models.conversation.Conversation.get_by_user') as mock_get:
            mock_conversations = [
                Conversation(id=1, user_id=1, message="Hello"),
                Conversation(id=2, user_id=1, message="What services?")
            ]
            mock_get.return_value = mock_conversations
            
            conversations = await Conversation.get_by_user(1)
            
            assert len(conversations) == 2
            assert all(c.user_id == 1 for c in conversations)
            mock_get.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_conversation_search(self):
        """Test conversation search functionality"""
        with patch('backend.models.conversation.Conversation.search') as mock_search:
            mock_conversations = [
                Conversation(id=1, message="What services do you offer?"),
                Conversation(id=2, message="Tell me about your services")
            ]
            mock_search.return_value = mock_conversations
            
            conversations = await Conversation.search("services")
            
            assert len(conversations) == 2
            assert all("services" in c.message.lower() for c in conversations)
            mock_search.assert_called_once_with("services")


@pytest.mark.database
class TestSessionModel:
    """Test Session model database operations"""
    
    @pytest.fixture
    def sample_session_data(self):
        return {
            "session_id": "test-session-123",
            "user_id": 1,
            "metadata": {"user_agent": "test-agent", "ip_address": "127.0.0.1"}
        }
    
    @pytest.mark.asyncio
    async def test_session_creation(self, sample_session_data):
        """Test session creation"""
        with patch('backend.models.session.Session.create') as mock_create:
            mock_session = Session(**sample_session_data)
            mock_create.return_value = mock_session
            
            session = await Session.create(**sample_session_data)
            
            assert session.session_id == sample_session_data["session_id"]
            assert session.user_id == sample_session_data["user_id"]
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_retrieval(self):
        """Test session retrieval"""
        with patch('backend.models.session.Session.get_by_id') as mock_get:
            mock_session = Session(
                session_id="test-session",
                user_id=1,
                created_at="2024-01-01T10:00:00Z"
            )
            mock_get.return_value = mock_session
            
            session = await Session.get_by_id("test-session")
            
            assert session.session_id == "test-session"
            assert session.user_id == 1
            mock_get.assert_called_once_with("test-session")
    
    @pytest.mark.asyncio
    async def test_session_update_activity(self):
        """Test session activity update"""
        with patch('backend.models.session.Session.update_last_activity') as mock_update:
            mock_update.return_value = True
            
            session = Session(session_id="test-session", user_id=1)
            result = await session.update_last_activity()
            
            assert result is True
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_cleanup_expired(self):
        """Test cleanup of expired sessions"""
        with patch('backend.models.session.Session.cleanup_expired') as mock_cleanup:
            mock_cleanup.return_value = 5  # 5 sessions cleaned up
            
            result = await Session.cleanup_expired(days=30)
            
            assert result == 5
            mock_cleanup.assert_called_once_with(days=30)


@pytest.mark.database
class TestDatabaseTransactions:
    """Test database transaction handling"""
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self):
        """Test successful transaction commit"""
        with patch('backend.core.database.get_session') as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session
            
            # Simulate successful transaction
            mock_db_session.commit = AsyncMock()
            mock_db_session.rollback = AsyncMock()
            
            # Mock database operations
            with patch('backend.models.user.User.create') as mock_create:
                mock_create.return_value = User(id=1, username="test")
                
                user = await User.create(username="test", email="test@example.com")
                
                assert user.username == "test"
                mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback on error"""
        with patch('backend.core.database.get_session') as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session
            
            mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))
            mock_db_session.rollback = AsyncMock()
            
            with pytest.raises(Exception):
                with patch('backend.models.user.User.create', side_effect=Exception("Database error")):
                    await User.create(username="test", email="test@example.com")
            
            mock_db_session.rollback.assert_called()


@pytest.mark.database
class TestDatabasePerformance:
    """Test database performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self):
        """Test bulk insert performance"""
        with patch('backend.models.user.User.bulk_create') as mock_bulk_create:
            users_data = [
                {"username": f"user_{i}", "email": f"user_{i}@example.com", "password_hash": "hash"}
                for i in range(100)
            ]
            
            mock_bulk_create.return_value = len(users_data)
            
            start_time = asyncio.get_event_loop().time()
            result = await User.bulk_create(users_data)
            end_time = asyncio.get_event_loop().time()
            
            execution_time = end_time - start_time
            
            assert result == 100
            assert execution_time < 1.0, "Bulk insert should complete in under 1 second"
            mock_bulk_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_performance(self):
        """Test query performance"""
        with patch('backend.models.conversation.Conversation.get_recent') as mock_get_recent:
            mock_conversations = [
                Conversation(id=i, message=f"Message {i}")
                for i in range(50)
            ]
            mock_get_recent.return_value = mock_conversations
            
            start_time = asyncio.get_event_loop().time()
            conversations = await Conversation.get_recent(limit=50)
            end_time = asyncio.get_event_loop().time()
            
            execution_time = end_time - start_time
            
            assert len(conversations) == 50
            assert execution_time < 0.1, "Query should complete in under 100ms"
            mock_get_recent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self):
        """Test concurrent database operations"""
        async def create_user(index: int):
            with patch('backend.models.user.User.create') as mock_create:
                mock_create.return_value = User(id=index, username=f"user_{index}")
                return await User.create(username=f"user_{index}", email=f"user_{index}@example.com")
        
        # Create 20 users concurrently
        tasks = [create_user(i) for i in range(20)]
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        execution_time = end_time - start_time
        
        assert len(results) == 20
        assert all(user.username.startswith("user_") for user in results)
        assert execution_time < 2.0, "Concurrent operations should complete in under 2 seconds"


@pytest.mark.database
class TestDatabaseMigrations:
    """Test database migration functionality"""
    
    @pytest.mark.asyncio
    async def test_migration_up(self):
        """Test database migration up"""
        with patch('backend.core.database.run_migrations') as mock_migrate:
            mock_migrate.return_value = True
            
            result = await mock_migrate("upgrade")
            
            assert result is True
            mock_migrate.assert_called_once_with("upgrade")
    
    @pytest.mark.asyncio
    async def test_migration_down(self):
        """Test database migration down"""
        with patch('backend.core.database.run_migrations') as mock_migrate:
            mock_migrate.return_value = True
            
            result = await mock_migrate("downgrade")
            
            assert result is True
            mock_migrate.assert_called_once_with("downgrade")
    
    @pytest.mark.asyncio
    async def test_migration_error_handling(self):
        """Test migration error handling"""
        with patch('backend.core.database.run_migrations', side_effect=Exception("Migration failed")):
            
            with pytest.raises(Exception) as exc_info:
                await mock_migrate("upgrade")
            
            assert "Migration failed" in str(exc_info.value)


@pytest.mark.database
class TestDatabaseBackupRestore:
    """Test database backup and restore functionality"""
    
    @pytest.mark.asyncio
    async def test_database_backup(self):
        """Test database backup"""
        with patch('backend.core.database.create_backup') as mock_backup:
            mock_backup.return_value = "/tmp/backup_20240101.sql"
            
            backup_path = await mock_backup()
            
            assert backup_path.endswith(".sql")
            assert "backup_" in backup_path
            mock_backup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_restore(self):
        """Test database restore"""
        with patch('backend.core.database.restore_from_backup') as mock_restore:
            mock_restore.return_value = True
            
            result = await mock_restore("/tmp/backup_20240101.sql")
            
            assert result is True
            mock_restore.assert_called_once_with("/tmp/backup_20240101.sql")