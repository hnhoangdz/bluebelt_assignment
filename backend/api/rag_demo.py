"""
RAG Demo API endpoints for testing the complete pipeline
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from ..services.rag_service import get_rag_service
from ..services.embedding_service import get_embedding_service
from ..services.memory_manager import get_memory_manager
from ..core.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag-demo", tags=["RAG Demo"])

class QueryRequest(BaseModel):
    query: str
    user_id: str = "demo_user"
    session_id: Optional[str] = None
    
class EmbeddingRequest(BaseModel):
    text: str

class InitializeRequest(BaseModel):
    force_refresh: bool = False

@router.post("/initialize")
async def initialize_embeddings(request: InitializeRequest):
    """Initialize embeddings and vector database"""
    try:
        embedding_service = await get_embedding_service()
        qdrant_client = await get_qdrant_client()
        
        # Check Qdrant health
        if not await qdrant_client.health_check():
            raise HTTPException(status_code=503, detail="Qdrant service unavailable")
        
        # Initialize embeddings
        success = await embedding_service.initialize_embeddings(
            force_refresh=request.force_refresh
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to initialize embeddings")
        
        # Get collection stats
        offerings_info = await qdrant_client.get_collection_info("company_offerings")
        faq_info = await qdrant_client.get_collection_info("faq")
        
        return {
            "status": "success",
            "message": "Embeddings initialized successfully",
            "collections": {
                "company_offerings": offerings_info,
                "faq": faq_info
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@router.post("/query")
async def process_query(request: QueryRequest):
    """Process a query through the complete RAG pipeline"""
    try:
        rag_service = await get_rag_service()
        
        # Generate session_id if not provided
        session_id = request.session_id or f"demo_session_{request.user_id}"
        
        # Process query through RAG pipeline
        response_data = await rag_service.process_query(
            user_query=request.query,
            user_id=request.user_id,
            session_id=session_id,
            conversation_history=[]  # Empty for demo
        )
        
        return {
            "status": "success",
            "user_query": request.query,
            "session_id": session_id,
            "response": response_data.get("response", ""),
            "metadata": {
                "intent": response_data.get("routing_info", {}).get("intent", "unknown"),
                "confidence": response_data.get("routing_info", {}).get("confidence", 0),
                "sources_used": len(response_data.get("sources", [])),
                "context_used": response_data.get("context_used", {}),
                "response_time": response_data.get("metadata", {}).get("timestamp", "")
            },
            "sources": response_data.get("sources", []),
            "query_processing": response_data.get("query_processing", {})
        }
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.post("/search")
async def search_knowledge_base(request: QueryRequest):
    """Search the knowledge base using vector similarity"""
    try:
        embedding_service = await get_embedding_service()
        
        results = await embedding_service.search_similar_content(
            query=request.query,
            collection_type="both",
            limit=5,
            score_threshold=0.5
        )
        
        return {
            "status": "success",
            "query": request.query,
            "results_count": len(results),
            "results": [
                {
                    "title": result.get("payload", {}).get("title", ""),
                    "content": result.get("payload", {}).get("content", "")[:200] + "...",
                    "category": result.get("payload", {}).get("category", ""),
                    "type": result.get("payload", {}).get("type", ""),
                    "score": result.get("score", 0)
                }
                for result in results
            ]
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session"""
    try:
        memory_manager = await get_memory_manager()
        
        history = await memory_manager.get_conversation_history(session_id)
        session_info = await memory_manager.get_session_info(session_id)
        
        return {
            "status": "success",
            "session_id": session_id,
            "session_info": session_info,
            "conversation_history": history
        }
        
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session history: {str(e)}")

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for a session"""
    try:
        memory_manager = await get_memory_manager()
        
        success = await memory_manager.clear_session_history(session_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Session {session_id} cleared successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found or could not be cleared")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check for RAG system components"""
    try:
        qdrant_client = await get_qdrant_client()
        
        # Check Qdrant
        qdrant_healthy = await qdrant_client.health_check()
        
        # Get collection info
        collections = {}
        if qdrant_healthy:
            try:
                collections["company_offerings"] = await qdrant_client.get_collection_info("company_offerings")
                collections["faq"] = await qdrant_client.get_collection_info("faq")
            except Exception as e:
                logger.warning(f"Could not get collection info: {e}")
        
        return {
            "status": "healthy" if qdrant_healthy else "unhealthy",
            "components": {
                "qdrant": "healthy" if qdrant_healthy else "unhealthy",
                "collections": collections
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }

@router.post("/embed")
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding for text (for testing)"""
    try:
        embedding_service = await get_embedding_service()
        
        embedding = await embedding_service.generate_embedding(request.text)
        
        return {
            "status": "success",
            "text": request.text,
            "embedding_dimension": len(embedding),
            "embedding_preview": embedding[:5]  # Show first 5 dimensions
        }
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")