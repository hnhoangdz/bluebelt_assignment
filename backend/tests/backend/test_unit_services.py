"""
Unit tests for core services
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
from typing import List, Dict, Any

from backend.services.auth_service import AuthService
from backend.services.rag_service import RAGService
from backend.services.embedding_service import EmbeddingService
from backend.services.query_processor import QueryProcessor, QueryIntent, QueryType


class TestAuthService:
    """Test cases for AuthService"""
    
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_password_hashing(self, auth_service):
        """Test password hashing and verification"""
        password = "testpassword123"
        
        # Test hashing
        hashed = await auth_service.hash_password(password)
        assert hashed != password
        assert len(hashed) > 0
        
        # Test verification
        is_valid = await auth_service.verify_password(password, hashed)
        assert is_valid is True
        
        # Test invalid password
        is_invalid = await auth_service.verify_password("wrongpassword", hashed)
        assert is_invalid is False
    
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_jwt_token_creation(self, auth_service):
        """Test JWT token creation and validation"""
        user_data = {"user_id": "123", "username": "testuser"}
        
        # Create token
        token = await auth_service.create_access_token(user_data)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Validate token
        decoded_data = await auth_service.decode_access_token(token)
        assert decoded_data["user_id"] == "123"
        assert decoded_data["username"] == "testuser"
    
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_invalid_jwt_token(self, auth_service):
        """Test handling of invalid JWT tokens"""
        invalid_token = "invalid.jwt.token"
        
        decoded_data = await auth_service.decode_access_token(invalid_token)
        assert decoded_data is None
    
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_user_registration(self, auth_service, sample_user_data):
        """Test user registration process"""
        with patch.object(auth_service, '_user_exists', return_value=False), \
             patch.object(auth_service, '_create_user', return_value={"id": "123", "username": "testuser"}):
            
            result = await auth_service.register_user(
                username=sample_user_data["username"],
                email=sample_user_data["email"],
                password=sample_user_data["password"],
                full_name=sample_user_data["full_name"]
            )
            
            assert result is not None
            assert result["username"] == "testuser"
    
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_user_authentication(self, auth_service, sample_login_data):
        """Test user authentication"""
        mock_user = {
            "id": "123",
            "username": "testuser",
            "password_hash": "hashed_password"
        }
        
        with patch.object(auth_service, '_get_user_by_username', return_value=mock_user), \
             patch.object(auth_service, 'verify_password', return_value=True):
            
            result = await auth_service.authenticate_user(
                username=sample_login_data["username"],
                password=sample_login_data["password"]
            )
            
            assert result is not None
            assert result["username"] == "testuser"


class TestQueryProcessor:
    """Test cases for QueryProcessor"""
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_query_rewriting(self, query_processor):
        """Test query rewriting functionality"""
        original_query = "What services do you offer?"
        
        with patch.object(query_processor.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "What specific services does Dextrends offer?"
            mock_create.return_value = mock_response
            
            rewritten = await query_processor.rewrite_query(original_query)
            
            assert rewritten != original_query
            assert "Dextrends" in rewritten
            mock_create.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_intent_classification(self, query_processor):
        """Test intent classification"""
        query = "What payment services do you provide?"
        
        with patch.object(query_processor.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"intent": "service_inquiry", "confidence": 0.95}'
            mock_create.return_value = mock_response
            
            intent, confidence = await query_processor.classify_intent(query)
            
            assert intent == QueryIntent.SERVICE_INQUIRY
            assert confidence == 0.95
            mock_create.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_query_type_classification(self, query_processor):
        """Test query type classification"""
        query = "What blockchain services do you offer?"
        intent = QueryIntent.SERVICE_INQUIRY
        
        with patch.object(query_processor.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"query_type": "offering", "confidence": 0.90}'
            mock_create.return_value = mock_response
            
            query_type, confidence = await query_processor.classify_query_type(query, intent)
            
            assert query_type == QueryType.OFFERING
            assert confidence == 0.90
            mock_create.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_query_routing(self, query_processor):
        """Test query routing logic"""
        intent = QueryIntent.SERVICE_INQUIRY
        query_type = QueryType.OFFERING
        confidence = 0.85
        
        routing_config = query_processor.route_query(intent, query_type, confidence)
        
        assert routing_config["use_rag"] is True
        assert routing_config["search_collections"] == ["offerings"]
        assert routing_config["response_style"] == "detailed"
        assert routing_config["intent"] == "service_inquiry"
        assert routing_config["query_type"] == "offering"
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_complete_query_processing(self, query_processor):
        """Test complete query processing pipeline"""
        user_query = "What services does Dextrends offer?"
        
        with patch.object(query_processor, 'rewrite_query', return_value="What specific services does Dextrends provide?"), \
             patch.object(query_processor, 'classify_intent', return_value=(QueryIntent.SERVICE_INQUIRY, 0.95)), \
             patch.object(query_processor, 'classify_query_type', return_value=(QueryType.OFFERING, 0.90)), \
             patch.object(query_processor, 'enhance_query_with_keywords', return_value="Enhanced query"):
            
            result = await query_processor.process_query(user_query)
            
            assert result["original_query"] == user_query
            assert result["intent"] == "service_inquiry"
            assert result["query_type"] == "offering"
            assert result["intent_confidence"] == 0.95
            assert result["type_confidence"] == 0.90


class TestEmbeddingService:
    """Test cases for EmbeddingService"""
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_generate_embedding(self, embedding_service):
        """Test embedding generation"""
        text = "Test text for embedding"
        
        embedding = await embedding_service.generate_embedding(text)
        
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # OpenAI embedding dimension
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_generate_batch_embeddings(self, embedding_service):
        """Test batch embedding generation"""
        texts = ["Text 1", "Text 2", "Text 3"]
        
        embeddings = await embedding_service.generate_batch_embeddings(texts)
        
        assert embeddings is not None
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_text_cleaning(self, embedding_service):
        """Test text cleaning functionality"""
        dirty_text = "  This   is   messy   text   with   extra   spaces  "
        
        cleaned = embedding_service._clean_text(dirty_text)
        
        assert cleaned == "This is messy text with extra spaces"
        assert cleaned.strip() == cleaned
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_point_id_generation(self, embedding_service):
        """Test unique point ID generation"""
        content = "Test content"
        source = "test_source"
        
        point_id = embedding_service._generate_point_id(content, source)
        
        assert point_id is not None
        assert isinstance(point_id, str)
        assert len(point_id) > 0
        
        # Same content should generate same ID
        point_id2 = embedding_service._generate_point_id(content, source)
        assert point_id == point_id2
        
        # Different content should generate different ID
        point_id3 = embedding_service._generate_point_id("Different content", source)
        assert point_id != point_id3
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_search_similar_content(self, embedding_service):
        """Test similar content search"""
        query = "payment services"
        
        with patch.object(embedding_service, 'generate_embedding', return_value=[0.1] * 1536):
            results = await embedding_service.search_similar_content(
                query=query,
                collection_type="offerings",
                limit=5,
                score_threshold=0.7
            )
            
            assert isinstance(results, list)
            # Results depend on mock data, so just verify structure


class TestRAGService:
    """Test cases for RAGService"""
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_context_string_building(self, rag_service):
        """Test context string building"""
        context = {
            "vector_search": [
                {
                    "title": "Test Service",
                    "content": "Test content",
                    "score": 0.85
                }
            ],
            "mem0_memories": [
                {
                    "content": "Previous interaction",
                    "score": 0.75
                }
            ]
        }
        
        routing_config = {"response_style": "informative"}
        context_string = rag_service._build_context_string(context, routing_config)
        
        assert "Test Service" in context_string
        assert "Test content" in context_string
        assert "Previous interaction" in context_string
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_conversation_context_building(self, rag_service):
        """Test conversation context building"""
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What services do you offer?"}
        ]
        
        context_string = rag_service._build_conversation_context(conversation_history)
        
        assert "User: Hello" in context_string
        assert "Assistant: Hi there!" in context_string
        assert "User: What services do you offer?" in context_string
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_system_prompt_generation(self, rag_service):
        """Test system prompt generation"""
        response_style = "professional"
        intent = "service_inquiry"
        
        system_prompt = rag_service._get_system_prompt(response_style, intent)
        
        assert "Dextrends" in system_prompt
        assert "professional" in system_prompt.lower()
        assert "Digital Payment Solutions" in system_prompt
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_source_extraction(self, rag_service):
        """Test source extraction from context"""
        context = {
            "vector_search": [
                {
                    "type": "service",
                    "title": "Payment Solutions",
                    "category": "Payment Services",
                    "score": 0.85
                }
            ],
            "mem0_memories": [
                {
                    "session_id": "test-session",
                    "score": 0.75
                }
            ]
        }
        
        sources = rag_service._extract_sources(context)
        
        assert len(sources) == 2
        assert sources[0]["type"] == "service"
        assert sources[0]["title"] == "Payment Solutions"
        assert sources[1]["type"] == "Previous Interaction"
    
    @pytest.mark.unit
    @pytest.mark.rag
    async def test_complete_rag_processing(self, rag_service):
        """Test complete RAG processing pipeline"""
        user_query = "What payment services do you offer?"
        user_id = "test-user"
        session_id = "test-session"
        
        with patch('backend.services.rag_service.get_query_processor') as mock_get_processor, \
             patch.object(rag_service, 'retrieve_context') as mock_retrieve, \
             patch.object(rag_service, 'generate_response') as mock_generate:
            
            # Mock query processor
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = {
                "enhanced_query": "Enhanced query",
                "routing": {"use_rag": True, "search_collections": ["offerings"]}
            }
            mock_get_processor.return_value = mock_processor
            
            # Mock context retrieval
            mock_retrieve.return_value = {"vector_search": [], "mem0_memories": []}
            
            # Mock response generation
            mock_generate.return_value = {
                "response": "Test response",
                "sources": [],
                "context_used": {},
                "routing_info": {},
                "metadata": {}
            }
            
            result = await rag_service.process_query(user_query, user_id, session_id)
            
            assert "response" in result
            assert "query_processing" in result
            mock_processor.process_query.assert_called_once()
            mock_retrieve.assert_called_once()
            mock_generate.assert_called_once()


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling across services"""
    
    async def test_auth_service_error_handling(self, auth_service):
        """Test AuthService error handling"""
        # Test with invalid input
        result = await auth_service.register_user("", "", "", "")
        assert result is None
    
    async def test_query_processor_error_handling(self, query_processor):
        """Test QueryProcessor error handling"""
        with patch.object(query_processor.client.chat.completions, 'create', side_effect=Exception("API Error")):
            # Should return original query on error
            result = await query_processor.rewrite_query("test query")
            assert result == "test query"
    
    async def test_embedding_service_error_handling(self, embedding_service):
        """Test EmbeddingService error handling"""
        with patch.object(embedding_service.client.embeddings, 'create', side_effect=Exception("API Error")):
            # Should raise exception
            with pytest.raises(Exception):
                await embedding_service.generate_embedding("test text")