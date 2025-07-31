"""
Chat API routes for conversation management and AI responses
"""

import time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.redis_client import get_redis_client
from ..services.auth_service import AuthService
from ..services.chat_service import ChatService
from ..models.user import User
from ..models.session import Session as UserSession
from .schemas import (
    ChatMessage, ChatResponse, ConversationHistory, ConversationItem,
    SessionInfo, ErrorResponse, SuccessResponse, PaginationParams,
    MemorySearchRequest, MemorySearchResponse
)

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()
chat_service = ChatService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    return user

@router.post("/send", response_model=ChatResponse)
async def send_message(
    chat_data: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    Send a message and get AI response using complete RAG pipeline with mem0 integration
    
    Pipeline:
    1. Receive request with user_id, session_id, query
    2. RAG rewrite and classify query, search FAQ and offerings from Qdrant
    3. Mem0 search related info based on user_id and session_id/run_id
    4. Pass all relevant context to LLM for response generation
    5. Return final response and sources from Qdrant collections
    6. Store final response in mem0 based on user_id and session_id/run_id
    """
    start_time = time.time()
    
    try:
        # Import required services
        from ..services.rag_service import get_rag_service
        from ..services.memory_service import MemoryService
        
        # Get services
        rag_service = await get_rag_service()
        memory_service = MemoryService()
        
        # Step 1: Process complete RAG pipeline
        # This handles: query rewrite, classification, Qdrant search, mem0 search, LLM generation
        rag_response = await rag_service.process_query(
            user_query=chat_data.query,
            user_id=chat_data.user_id,
            session_id=chat_data.session_id,
            conversation_history=None  # We could get this from memory if needed
        )
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Step 2: Prepare response with all context and sources
        return ChatResponse(
            response=rag_response["response"],
            conversation_id=f"rag-{chat_data.session_id}",
            sources=rag_response.get("sources", []),
            context_used=rag_response.get("context_used", {}),
            routing_info=rag_response.get("routing_info", {}),
            tokens_used=0,  # RAG service doesn't track this currently
            response_time_ms=response_time_ms,
            model_used=rag_response.get("metadata", {}).get("model_used", ""),
            metadata=rag_response.get("metadata", {})
        )
        
    except Exception as e:
        print(f"Chat API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.get("/conversations", response_model=ConversationHistory)
async def get_conversation_history(
    session_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get conversation history for current user or specific session
    """
    from ..models.conversation import Conversation
    
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    
    if session_id:
        query = query.filter(Conversation.session_id == session_id)
    
    conversations = query.order_by(Conversation.timestamp.desc()).limit(limit).all()
    
    # Convert to response format
    conversation_items = []
    for conv in conversations:
        conversation_items.append(ConversationItem(
            id=str(conv.id),
            message=conv.message,
            response=conv.response,
            timestamp=conv.timestamp,
            tokens_used=conv.tokens_used,
            response_time_ms=conv.response_time_ms,
            is_error=conv.is_error
        ))
    
    return ConversationHistory(
        conversations=conversation_items,
        total_count=len(conversation_items)
    )


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's chat sessions
    """
    try:
        # Get user sessions from auth service
        sessions = auth_service.get_user_sessions(db, str(current_user.id), active_only=True)
        
        # Convert to response format
        session_list = []
        for session in sessions:
            session_list.append({
                "id": session.id,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "is_active": session.is_active,
                "last_activity": session.last_activity.isoformat() if session.last_activity else None
            })
        
        return session_list
    except Exception as e:
        print(f"Error loading user sessions: {e}")
        return []


@router.get("/history/{session_id}")
async def get_conversation_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get conversation history for a session
    """
    try:
        from ..models.conversation import Conversation
        
        # Verify session belongs to current user
        session = auth_service.get_user_session(db, session_id)
        if not session or str(session.user_id) != str(current_user.id):
            return {
                "conversations": [],
                "total_count": 0
            }
        
        # Get conversations for this session
        conversations = db.query(Conversation).filter(
            Conversation.user_id == current_user.id,
            Conversation.session_id == session_id
        ).order_by(Conversation.timestamp.asc()).all()
        
        # Convert to response format
        conversation_items = []
        for conv in conversations:
            conversation_items.append({
                "id": str(conv.id),
                "message": conv.message,
                "response": conv.response,
                "timestamp": conv.timestamp.isoformat() if conv.timestamp else None,
                "tokens_used": conv.tokens_used or 0,
                "response_time_ms": conv.response_time_ms or 0,
                "is_error": conv.is_error or False
            })
        
        return {
            "conversations": conversation_items,
            "total_count": len(conversation_items)
        }
    except Exception as e:
        print(f"Error loading conversation history for session {session_id}: {e}")
        return {
            "conversations": [],
            "total_count": 0
        }


@router.post("/session")
async def create_new_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new chat session
    """
    try:
        # Create user session using auth service
        session = auth_service.create_user_session(
            db=db,
            user=current_user,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host
        )
        
        # Return session data
        return {
            "id": session.id,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "is_active": session.is_active
        }
    except Exception as e:
        print(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a chat session and its conversations
    """
    try:
        # Check if session belongs to current user
        session = auth_service.get_user_session(db, session_id)
        if not session or str(session.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Delete all conversations for this session
        from ..models.conversation import Conversation
        db.query(Conversation).filter(
            Conversation.user_id == current_user.id,
            Conversation.session_id == session_id
        ).delete(synchronize_session=False)
        
        # Invalidate/delete the session
        auth_service.invalidate_session(db, session_id)
        
        # Commit the changes
        db.commit()
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )


@router.post("/message", response_model=ChatResponse)
async def chat_with_memory(
    chat_data: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    Chat endpoint with memory integration - similar to send but with enhanced memory features
    
    Pipeline:
    1. Receive request with user_id, session_id, query
    2. Search memory for related information based on user_id and session_id
    3. RAG rewrite and classify query, search FAQ and offerings from Qdrant
    4. Mem0 search related info based on user_id and session_id/run_id  
    5. Pass all relevant context (memory + RAG) to LLM for response generation
    6. Return final response and sources from Qdrant collections
    7. Store final response in mem0 based on user_id and session_id/run_id
    """
    start_time = time.time()
    
    try:
        # Import required services
        from ..services.rag_service import get_rag_service
        from ..services.memory_service import MemoryService
        
        # Get services
        rag_service = await get_rag_service()
        memory_service = MemoryService()
        
        # Step 1: Search memory for related information
        # First search session-specific memories
        session_memory_results = await memory_service.search_memory(
            user_id=chat_data.user_id,
            query=chat_data.query,
            session_id=chat_data.session_id
        )
        
        # Then search all user memories (across sessions) for broader context
        user_memory_results = await memory_service.search_memory(
            user_id=chat_data.user_id,
            query=chat_data.query,
            session_id=None  # Search across all sessions
        )
        
        # Combine results, prioritizing session-specific ones
        memory_results = session_memory_results + [
            result for result in user_memory_results 
            if result not in session_memory_results
        ]
        
        # Step 2: Get conversation context for enhanced personalization
        conversation_context = await memory_service.get_conversation_context(
            user_id=chat_data.user_id,
            limit=5
        )
        
        # Step 3: Process complete RAG pipeline with memory context
        # This handles: query rewrite, classification, Qdrant search, mem0 search, LLM generation
        rag_response = await rag_service.process_query(
            user_query=chat_data.query,
            user_id=chat_data.user_id,
            session_id=chat_data.session_id,
            conversation_history=conversation_context  # Pass memory context to RAG
        )
        
        # Step 4: Store the interaction in memory for future personalization
        await memory_service.add_memory(
            user_id=chat_data.user_id,
            session_id=chat_data.session_id,
            message=chat_data.query,
            response=rag_response["response"],
            context={
                "sources": rag_response.get("sources", []),
                "routing_info": rag_response.get("routing_info", {}),
                "memory_used": len(memory_results) > 0,
                "memory_results_count": len(memory_results)
            }
        )
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Step 5: Store conversation in database for history persistence
        try:
            from ..models.conversation import Conversation
            from datetime import datetime
            import uuid
            
            conversation = Conversation(
                id=uuid.uuid4(),
                user_id=chat_data.user_id,
                session_id=chat_data.session_id,
                message=chat_data.query,
                response=rag_response["response"],
                timestamp=datetime.utcnow(),
                tokens_used=0,  # RAG service doesn't track this currently
                response_time_ms=response_time_ms,
                is_error=False
            )
            db.add(conversation)
            db.commit()
        except Exception as e:
            print(f"Error storing conversation in database: {e}")
            # Don't fail the request if database storage fails
            pass
        
        # Step 6: Prepare enhanced response with memory integration info
        return ChatResponse(
            response=rag_response["response"],
            conversation_id=f"chat-memory-{chat_data.session_id}",
            sources=rag_response.get("sources", []),
            context_used={
                **rag_response.get("context_used", {}),
                "memory_results": memory_results,
                "conversation_context": conversation_context,
                "memory_integration": True
            },
            routing_info=rag_response.get("routing_info", {}),
            tokens_used=0,  # RAG service doesn't track this currently
            response_time_ms=response_time_ms,
            model_used=rag_response.get("metadata", {}).get("model_used", ""),
            metadata={
                **rag_response.get("metadata", {}),
                "memory_enhanced": True,
                "memory_results_count": len(memory_results),
                "conversation_context_used": len(conversation_context) > 0
            }
        )
        
    except Exception as e:
        print(f"Chat with memory API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response with memory integration: {str(e)}"
        )


@router.get("/memory", response_model=dict)
async def get_user_memory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's memory context from Mem0
    """
    from ..services.memory_service import MemoryService
    
    memory_service = MemoryService()
    memory = await memory_service.get_user_memory(str(current_user.id))
    
    return {
        "user_id": str(current_user.id),
        "memory": memory or {}
    }


@router.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search user's memory for relevant information with session_id support
    """
    from ..services.memory_service import MemoryService
    
    memory_service = MemoryService()
    results = await memory_service.search_memory(
        user_id=str(current_user.id), 
        query=request.query,
        session_id=request.session_id
    )
    
    return MemorySearchResponse(
        user_id=str(current_user.id),
        query=request.query,
        session_id=request.session_id,
        results=results,
        total_count=len(results)
    ) 