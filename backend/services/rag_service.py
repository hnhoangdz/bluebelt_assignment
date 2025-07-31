"""
RAG (Retrieval-Augmented Generation) Service for Dextrends AI Chatbot
Integrates vector search with Mem0 for comprehensive knowledge retrieval
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

import openai
try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MemoryClient = None
    MEM0_AVAILABLE = False

from ..config import settings
from .embedding_service import get_embedding_service
from .query_processor import get_query_processor
from ..core.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)

class RAGService:
    """
    Retrieval-Augmented Generation service with Mem0 integration
    """
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
        self.mem0_client = None
        self.initialize_mem0()
    
    def initialize_mem0(self):
        """Initialize Mem0 client"""
        try:
            if not MEM0_AVAILABLE:
                logger.warning("Mem0 not available, using fallback memory management")
                self.mem0_client = None
                return
                
            if settings.mem0_api_key:
                # Initialize MemoryClient with API credentials
                self.mem0_client = MemoryClient(
                    api_key=settings.mem0_api_key,
                    org_id=getattr(settings, 'mem0_org_id', None),
                    project_id=getattr(settings, 'mem0_project_id', None)
                )
                logger.info("MemoryClient initialized successfully")
            else:
                logger.warning("Mem0 API key not provided, using fallback memory management")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            self.mem0_client = None
    
    async def retrieve_context(
        self, 
        query: str, 
        user_id: str,
        session_id: str,
        routing_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context from multiple sources
        """
        try:
            context_sources = {
                "vector_search": [],
                "mem0_memories": [],
                "search_metadata": {}
            }
            
            # 1. Vector search in Qdrant
            if routing_config.get("use_rag", True):
                vector_results = await self._vector_search(query, routing_config)
                context_sources["vector_search"] = vector_results
            
            # 2. Mem0 long-term memory search (using session_id as run_id)
            if self.mem0_client:
                mem0_results = await self._mem0_search(query, user_id, session_id)
                context_sources["mem0_memories"] = mem0_results
            
            # 3. Compile search metadata
            context_sources["search_metadata"] = {
                "query": query,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "vector_results_count": len(context_sources["vector_search"]),
                "mem0_results_count": len(context_sources["mem0_memories"]),
                "routing_config": routing_config
            }
            
            logger.info(f"Retrieved context: {len(context_sources['vector_search'])} vector + {len(context_sources['mem0_memories'])} mem0 results")
            return context_sources
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return {
                "vector_search": [],
                "mem0_memories": [],
                "search_metadata": {"error": str(e)}
            }
    
    async def _vector_search(self, query: str, routing_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform vector search in Qdrant"""
        try:
            embedding_service = await get_embedding_service()
            
            # Determine search collections
            search_collections = routing_config.get("search_collections", ["both"])
            
            # Search for similar content
            if "both" in search_collections:
                collection_type = "both"
            elif "offerings" in search_collections:
                collection_type = "offerings"
            elif "faq" in search_collections:
                collection_type = "faq"
            else:
                collection_type = "both"
            
            results = await embedding_service.search_similar_content(
                query=query,
                collection_type=collection_type,
                limit=routing_config.get("search_limit", 5),
                score_threshold=routing_config.get("score_threshold", 0.7)
            )
            
            # Format results for context
            formatted_results = []
            for result in results:
                payload = result.get("payload", {})
                formatted_results.append({
                    "source": "vector_search",
                    "type": payload.get("type", "unknown"),
                    "title": payload.get("title", ""),
                    "content": payload.get("content", ""),
                    "category": payload.get("category", ""),
                    "score": result.get("score", 0),
                    "metadata": payload
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _mem0_search(self, query: str, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Search Mem0 for relevant memories using session_id as run_id, with fallback to user-wide search"""
        try:
            if not self.mem0_client:
                return []
            
            # First search session-specific memories using v2 API
            session_filters = {
                "AND": [
                    {"user_id": user_id},
                    {"run_id": session_id}
                ]
            }
            
            session_memories = await asyncio.to_thread(
                self.mem0_client.search,
                query=query,
                version="v2",
                filters=session_filters,
                top_k=3
            )
            
            # Then search all user memories (across sessions) for broader context using v2 API
            user_filters = {
                "user_id": user_id
            }
            
            user_memories = await asyncio.to_thread(
                self.mem0_client.search,
                query=query,
                version="v2",
                filters=user_filters,
                top_k=5
            )
            
            # Combine results, prioritizing session-specific ones
            memories = session_memories + [
                memory for memory in user_memories 
                if memory not in session_memories
            ]
            
            # Limit to top 5 total results
            memories = memories[:5]
            
            # Format memories for context
            formatted_memories = []
            for memory in memories:
                formatted_memories.append({
                    "source": "mem0_memory",
                    "type": "memory",
                    "content": memory.get("memory", ""),
                    "score": memory.get("score", 0),
                    "created_at": memory.get("created_at", ""),
                    "updated_at": memory.get("updated_at", ""),
                    "session_id": session_id,
                    "metadata": memory.get("metadata", {})
                })
            
            logger.debug(f"Found {len(formatted_memories)} relevant memories for session {session_id}")
            return formatted_memories
            
        except Exception as e:
            logger.error(f"Mem0 search failed: {e}")
            return []
    
    async def generate_response(
        self, 
        query: str, 
        context: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        routing_config: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate response using retrieved context and conversation history
        """
        try:
            # Build context string
            context_string = self._build_context_string(context, routing_config)
            
            # Build conversation context
            conversation_context = self._build_conversation_context(conversation_history)
            
            # Generate response
            response = await self._generate_llm_response(
                query, 
                context_string, 
                conversation_context, 
                routing_config
            )
            
            # Store interaction in Mem0 for long-term memory (using session_id as run_id)
            if self.mem0_client:
                await self._store_interaction_memory(query, response, user_id, session_id, context)
            
            # Prepare response with metadata
            response_data = {
                "response": response,
                "sources": self._extract_sources(context),
                "context_used": {
                    "vector_results": len(context.get("vector_search", [])),
                    "mem0_memories": len(context.get("mem0_memories", [])),
                    "conversation_messages": len(conversation_history) if conversation_history else 0
                },
                "routing_info": {
                    "intent": routing_config.get("intent", "unknown"),
                    "confidence": routing_config.get("confidence", 0),
                    "response_style": routing_config.get("response_style", "informative")
                },
                "metadata": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "model_used": settings.openai_model
                }
            }
            
            logger.info(f"Generated response for user {user_id} in session {session_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again or contact support if the issue persists.",
                "sources": [],
                "context_used": {},
                "routing_info": {},
                "metadata": {"error": str(e)}
            }
    
    def _build_context_string(self, context: Dict[str, Any], routing_config: Dict[str, Any]) -> str:
        """Build context string from retrieved information"""
        try:
            context_parts = []
            
            # Add vector search results
            vector_results = context.get("vector_search", [])
            if vector_results:
                context_parts.append("=== COMPANY INFORMATION ===")
                for result in vector_results[:3]:  # Top 3 results
                    title = result.get("title", "Information")
                    content = result.get("content", "")
                    score = result.get("score", 0)
                    context_parts.append(f"[{title}] (Relevance: {score:.2f})\n{content}\n")
            
            # Add Mem0 memories
            mem0_results = context.get("mem0_memories", [])
            if mem0_results:
                context_parts.append("=== PREVIOUS INTERACTIONS ===")
                for memory in mem0_results[:2]:  # Top 2 memories
                    content = memory.get("content", "")
                    context_parts.append(f"Previous context: {content}\n")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to build context string: {e}")
            return ""
    
    def _build_conversation_context(self, conversation_history: List[Dict[str, str]]) -> str:
        """Build conversation context from recent messages"""
        try:
            if not conversation_history:
                return ""
            
            # Get last 5 messages
            recent_messages = conversation_history[-5:]
            context_parts = []
            
            for msg in recent_messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                context_parts.append(f"{role.capitalize()}: {content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to build conversation context: {e}")
            return ""
    
    async def _generate_llm_response(
        self, 
        query: str, 
        context: str, 
        conversation_context: str,
        routing_config: Dict[str, Any]
    ) -> str:
        """Generate response using OpenAI"""
        try:
            # Build system prompt based on response style
            response_style = routing_config.get("response_style", "informative")
            intent = routing_config.get("intent", "unknown")
            
            system_prompt = self._get_system_prompt(response_style, intent)
            
            # Build user prompt
            user_prompt = f"""
User Query: {query}

Context Information:
{context if context else "No specific context available"}

Recent Conversation:
{conversation_context if conversation_context else "No previous conversation"}

Please provide a helpful and accurate response based on the available information about Dextrends services.
"""
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again."
    
    def _get_system_prompt(self, response_style: str, intent: str) -> str:
        """Get system prompt based on response style and intent"""
        base_prompt = """You are a helpful AI assistant for Dextrends, a leading technology company specializing in digital financial services and blockchain solutions. 
        
        Your role is to:
        1. Provide accurate information about Dextrends services and capabilities
        2. Answer questions professionally and helpfully
        3. Use the provided context information when available
        4. Be honest when you don't have specific information
        5. Maintain a professional yet approachable tone
        
        Company Focus Areas:
        - Digital Payment Solutions
        - Blockchain Asset Management  
        - Smart Contract Development
        - DeFi Integration
        - Identity Verification (KYC/AML)
        - Asset Tokenization
        - CBDC Solutions
        - Cryptocurrency Trading
        """
        
        style_additions = {
            "friendly": "Keep your responses warm and conversational.",
            "professional": "Maintain a formal, business-appropriate tone.",
            "technical": "Provide detailed technical information and explanations.",
            "conversational": "Use a natural, easy-going conversational style.",
            "authoritative": "Speak with confidence and expertise on the subject matter.",
            "helpful": "Focus on being maximally helpful and solution-oriented.",
            "detailed": "Provide comprehensive, thorough responses with examples.",
            "precise": "Give exact, specific information without unnecessary elaboration.",
            "step_by_step": "Break down complex topics into clear, actionable steps."
        }
        
        style_addition = style_additions.get(response_style, "")
        
        return f"{base_prompt}\n\nResponse Style: {style_addition}"
    
    def _extract_sources(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract source information for citation"""
        try:
            sources = []
            
            # Extract from vector search results
            for result in context.get("vector_search", []):
                sources.append({
                    "type": result.get("type", "unknown"),
                    "title": result.get("title", ""),
                    "category": result.get("category", ""),
                    "source": "Knowledge Base",
                    "relevance_score": result.get("score", 0)
                })
            
            # Extract from Mem0 memories
            for memory in context.get("mem0_memories", []):
                sources.append({
                    "type": "Previous Interaction",
                    "source": "Conversation History",
                    "session_id": memory.get("session_id", ""),
                    "relevance_score": memory.get("score", 0)
                })
            
            return sources[:5]  # Limit to top 5 sources
            
        except Exception as e:
            logger.error(f"Failed to extract sources: {e}")
            return []
    
    async def _store_interaction_memory(
        self, 
        query: str, 
        response: str, 
        user_id: str, 
        session_id: str,
        context: Dict[str, Any]
    ):
        """Store interaction in Mem0 for long-term memory using session_id as run_id"""
        try:
            if not self.mem0_client:
                return
            
            # Create memory entry using MemoryClient format
            messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": response[:500] + "..." if len(response) > 500 else response}
            ]
            
            # Add to MemoryClient with run_id and metadata
            await asyncio.to_thread(
                self.mem0_client.add,
                messages=messages,
                user_id=user_id,
                run_id=session_id,  # Use session_id as run_id for session-based memory storage
                version="v2",
                metadata={
                    "interaction_type": "qa",
                    "session_id": session_id,  # Keep in metadata for additional context
                    "timestamp": datetime.now().isoformat(),
                    "query_intent": context.get("search_metadata", {}).get("routing_config", {}).get("intent", "unknown")
                }
            )
            
            logger.debug(f"Stored interaction memory for user {user_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to store interaction memory: {e}")
    
    async def process_query(
        self, 
        user_query: str, 
        user_id: str,
        session_id: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Complete RAG pipeline: query processing + retrieval + generation
        """
        try:
            # Step 1: Process query (rewrite, classify, route)
            query_processor = await get_query_processor()
            processing_result = await query_processor.process_query(user_query, conversation_history)
            
            enhanced_query = processing_result["enhanced_query"]
            routing_config = processing_result["routing"]
            
            # Step 2: Retrieve context (including session_id for Mem0)
            context = await self.retrieve_context(enhanced_query, user_id, session_id, routing_config)
            
            # Step 3: Generate response (including session_id for Mem0 storage)
            response_data = await self.generate_response(
                user_query, 
                context, 
                conversation_history or [], 
                routing_config, 
                user_id,
                session_id
            )
            
            # Add query processing info to response
            response_data["query_processing"] = processing_result
            
            logger.info(f"RAG pipeline completed for user {user_id} in session {session_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "sources": [],
                "context_used": {},
                "routing_info": {},
                "metadata": {"error": str(e)}
            }


# Global RAG service instance
rag_service = RAGService()

async def get_rag_service() -> RAGService:
    """Get the global RAG service instance"""
    return rag_service