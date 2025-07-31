"""
Enhanced Chat service with RAG pipeline integration for Dextrends AI Chatbot
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
import logging

from ..config import settings
from ..models.user import User
from ..models.session import Session as UserSession
from ..models.conversation import Conversation
from .rag_service import get_rag_service
from .memory_manager import get_memory_manager
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class ChatService:
    """Enhanced Chat service with RAG pipeline integration"""
    
    def __init__(self):
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
    
    async def generate_response(
        self, 
        message: str, 
        user: User, 
        session: UserSession,
        db: Session,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Enhanced AI response generation with RAG pipeline:
        1. Store user message in short-term memory
        2. Get conversation history (last 3-5 messages)
        3. Process query through RAG pipeline (rewrite, classify, route)
        4. Retrieve context from vector search and Mem0 long-term memory
        5. Generate response using LLM with all context
        6. Store response in short-term memory and Mem0 long-term memory
        
        Returns:
            Tuple of (response_text, metadata)
        """
        start_time = time.time()
        
        try:
            user_id = str(user.id)
            session_id = session.id
            
            # Get services
            memory_manager = await get_memory_manager()
            rag_service = await get_rag_service()
            
            # Step 1: Store user message in short-term memory
            await memory_manager.add_user_message(session_id, message)
            
            # Step 2: Get conversation history (last 3-5 messages)
            conversation_history = await memory_manager.get_conversation_history(session_id)
            
            # Step 3-6: Process through RAG pipeline
            rag_response = await rag_service.process_query(
                user_query=message,
                user_id=user_id,
                session_id=session_id,
                conversation_history=conversation_history
            )
            
            response_text = rag_response.get("response", "I apologize, but I couldn't generate a response.")
            
            # Step 7: Store assistant response in short-term memory
            response_metadata = {
                "intent": rag_response.get("routing_info", {}).get("intent", "unknown"),
                "confidence": rag_response.get("routing_info", {}).get("confidence", 0),
                "sources_used": len(rag_response.get("sources", [])),
                "model_used": self.model
            }
            
            await memory_manager.add_assistant_message(
                session_id, 
                response_text, 
                response_metadata
            )
            
            # Step 8: Store conversation in database
            conversation = self._store_conversation(
                db=db,
                user_id=user_id,
                session_id=session_id,
                message=message,
                response=response_text,
                tokens_used=rag_response.get("metadata", {}).get("tokens_used", 0),
                response_time_ms=int((time.time() - start_time) * 1000),
                context={
                    "rag_response": rag_response,
                    "conversation_history_length": len(conversation_history)
                }
            )
            
            # Compile metadata
            metadata = {
                "conversation_id": conversation.id if conversation else None,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "model_used": self.model,
                "rag_metadata": rag_response.get("metadata", {}),
                "query_processing": rag_response.get("query_processing", {}),
                "context_used": rag_response.get("context_used", {}),
                "routing_info": rag_response.get("routing_info", {}),
                "sources": rag_response.get("sources", [])
            }
            
            logger.info(f"Generated response for user {user_id} in session {session_id}")
            return response_text, metadata
            
        except Exception as e:
            # Handle errors gracefully
            logger.error(f"Chat service error: {e}")
            error_message = "I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists."
            error_metadata = {
                "error": str(e),
                "response_time_ms": int((time.time() - start_time) * 1000),
                "model_used": self.model
            }
            
            # Store error conversation
            try:
                self._store_conversation(
                    db=db,
                    user_id=str(user.id) if user else "unknown",
                    session_id=session.id if session else "unknown",
                    message=message,
                    response=error_message,
                    tokens_used=0,
                    response_time_ms=error_metadata["response_time_ms"],
                    context={"error": str(e)},
                    is_error=True,
                    error_message=str(e)
                )
            except Exception as store_error:
                logger.error(f"Failed to store error conversation: {store_error}")
            
            return error_message, error_metadata
    
    async def _get_latest_conversation_history(self, db: Session, user_id: str, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """Get latest N conversation messages for context"""
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.session_id == session_id,
            Conversation.is_error == False
        ).order_by(Conversation.timestamp.desc()).limit(limit).all()
        
        # Reverse to get chronological order
        conversations.reverse()
        
        return [
            {
                "message": conv.message,
                "response": conv.response,
                "timestamp": conv.timestamp.isoformat() if conv.timestamp else None
            }
            for conv in conversations
        ]
    
    def _build_messages_with_memory(
        self, 
        message: str, 
        latest_messages: List[Dict[str, str]], 
        memory_results: List[Dict[str, Any]],
        user: User
    ) -> List[Dict[str, str]]:
        """Build messages array for OpenAI API with memory context"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add memory context to system message
        if memory_results:
            memory_context = "\n\nUser Memory Context:\n"
            for memory in memory_results:
                memory_context += f"- {memory.get('memory', memory)}\n"
            messages[0]["content"] += memory_context
        
        # Add user context
        user_context = f"\n\nUser Info:\n- Name: {user.full_name or user.username}\n"
        if user.preferences:
            user_context += f"- Preferences: {user.preferences}\n"
        messages[0]["content"] += user_context
        
        # Add latest conversation history
        for conv in latest_messages:
            messages.append({"role": "user", "content": conv["message"]})
            messages.append({"role": "assistant", "content": conv["response"]})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _build_messages(
        self, 
        message: str, 
        conversation_history: List[Dict[str, str]], 
        user_context: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Build messages array for OpenAI API"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add user context to system message
        if user_context:
            context_str = f"\n\nUser Context:\n- Name: {user_context.get('name', 'Unknown')}\n"
            if user_context.get('preferences'):
                context_str += f"- Preferences: {user_context['preferences']}\n"
            if user_context.get('interests'):
                context_str += f"- Interests: {user_context['interests']}\n"
            messages[0]["content"] += context_str
        
        # Add conversation history (last 10 messages to stay within token limits)
        for conv in conversation_history[-10:]:
            messages.append({"role": "user", "content": conv["message"]})
            messages.append({"role": "assistant", "content": conv["response"]})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    async def _get_conversation_history(self, db: Session, user_id: str, session_id: str) -> List[Dict[str, str]]:
        """Get recent conversation history for context"""
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.session_id == session_id,
            Conversation.is_error == False
        ).order_by(Conversation.timestamp.desc()).limit(10).all()
        
        # Reverse to get chronological order
        conversations.reverse()
        
        return [
            {
                "message": conv.message,
                "response": conv.response,
                "timestamp": conv.timestamp.isoformat() if conv.timestamp else None
            }
            for conv in conversations
        ]
    
    async def _get_user_context(self, user: User, session: UserSession) -> Dict[str, Any]:
        """Get user context for personalization"""
        context = {
            "name": user.full_name,
            "username": user.username,
            "preferences": user.preferences,
            "session_context": session.context,
            "session_state": session.state
        }
        
        # Get memory context from Mem0
        memory_context = await self.memory_service.get_user_memory(str(user.id))
        if memory_context:
            context.update(memory_context)
        
        return context
    
    def _store_conversation(
        self, 
        db: Session, 
        user_id: str, 
        session_id: str, 
        message: str, 
        response: str,
        tokens_used: int, 
        response_time_ms: int, 
        context: Optional[Dict[str, Any]] = None,
        is_error: bool = False,
        error_message: Optional[str] = None
    ) -> Conversation:
        """Store conversation in database"""
        conversation = Conversation(
            user_id=user_id,
            session_id=session_id,
            message=message,
            response=response,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            model_used=self.model,
            context=context or {},
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "user_agent": "Dextrends-Chatbot"
            }
        )
        
        if is_error:
            conversation.set_error(error_message or "Unknown error")
        else:
            conversation.set_success(tokens_used, response_time_ms, self.model)
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    async def get_conversation_summary(self, db: Session, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get summary of conversation session"""
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.session_id == session_id
        ).order_by(Conversation.timestamp.asc()).all()
        
        if not conversations:
            return {"message_count": 0, "total_tokens": 0, "avg_response_time": 0}
        
        total_tokens = sum(conv.tokens_used for conv in conversations)
        total_response_time = sum(conv.response_time_ms for conv in conversations)
        avg_response_time = total_response_time / len(conversations) if conversations else 0
        
        return {
            "message_count": len(conversations),
            "total_tokens": total_tokens,
            "avg_response_time": avg_response_time,
            "first_message": conversations[0].timestamp.isoformat() if conversations[0].timestamp else None,
            "last_message": conversations[-1].timestamp.isoformat() if conversations[-1].timestamp else None
        }
    
    async def clear_conversation_history(self, db: Session, user_id: str, session_id: str) -> bool:
        """Clear conversation history for a session"""
        try:
            db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id
            ).delete()
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False 