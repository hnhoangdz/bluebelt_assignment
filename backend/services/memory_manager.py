"""
Memory Management Service for Dextrends AI Chatbot
Handles short-term conversation memory and session management
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging

from ..core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Service for managing short-term conversation memory
    Stores and retrieves last 3-5 messages per session
    """
    
    def __init__(self):
        self.max_messages = 5  # Keep last 5 messages
        self.session_ttl = 3600  # 1 hour TTL for sessions
        self.memory_key_prefix = "chat_memory"
    
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a session (last 3-5 messages)
        """
        try:
            redis_client = await get_redis_client()
            
            # Get conversation history from Redis
            key = f"{self.memory_key_prefix}:{session_id}"
            history_data = await redis_client.get(key)
            
            if history_data:
                history = json.loads(history_data)
                messages = history.get("messages", [])
                
                # Return last max_messages
                recent_messages = messages[-self.max_messages:]
                
                logger.debug(f"Retrieved {len(recent_messages)} messages for session {session_id}")
                return recent_messages
            
            logger.debug(f"No conversation history found for session {session_id}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to conversation history
        """
        try:
            redis_client = await get_redis_client()
            
            # Get current history
            current_history = await self.get_conversation_history(session_id)
            
            # Create new message
            new_message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Add to history
            current_history.append(new_message)
            
            # Keep only last max_messages
            if len(current_history) > self.max_messages:
                current_history = current_history[-self.max_messages:]
            
            # Store back to Redis
            key = f"{self.memory_key_prefix}:{session_id}"
            history_data = {
                "session_id": session_id,
                "messages": current_history,
                "last_updated": datetime.now().isoformat()
            }
            
            await redis_client.setex(
                key, 
                self.session_ttl, 
                json.dumps(history_data, ensure_ascii=False)
            )
            
            logger.debug(f"Added {role} message to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message to history: {e}")
            return False
    
    async def add_user_message(self, session_id: str, message: str) -> bool:
        """Add user message to conversation history"""
        return await self.add_message(session_id, "user", message)
    
    async def add_assistant_message(
        self, 
        session_id: str, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add assistant message to conversation history"""
        return await self.add_message(session_id, "assistant", message, metadata)
    
    async def clear_session_history(self, session_id: str) -> bool:
        """Clear conversation history for a session"""
        try:
            redis_client = await get_redis_client()
            
            key = f"{self.memory_key_prefix}:{session_id}"
            result = await redis_client.delete(key)
            
            logger.info(f"Cleared conversation history for session {session_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to clear session history: {e}")
            return False
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information including message count and last activity"""
        try:
            redis_client = await get_redis_client()
            
            key = f"{self.memory_key_prefix}:{session_id}"
            history_data = await redis_client.get(key)
            
            if history_data:
                history = json.loads(history_data)
                messages = history.get("messages", [])
                
                return {
                    "session_id": session_id,
                    "message_count": len(messages),
                    "last_updated": history.get("last_updated"),
                    "first_message_time": messages[0]["timestamp"] if messages else None,
                    "last_message_time": messages[-1]["timestamp"] if messages else None,
                    "session_duration": self._calculate_session_duration(messages),
                    "participants": list(set(msg["role"] for msg in messages))
                }
            
            return {
                "session_id": session_id,
                "message_count": 0,
                "exists": False
            }
            
        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return {"session_id": session_id, "error": str(e)}
    
    def _calculate_session_duration(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Calculate session duration from first to last message"""
        try:
            if len(messages) < 2:
                return None
            
            first_time = datetime.fromisoformat(messages[0]["timestamp"])
            last_time = datetime.fromisoformat(messages[-1]["timestamp"])
            
            duration = last_time - first_time
            return str(duration)
            
        except Exception as e:
            logger.error(f"Failed to calculate session duration: {e}")
            return None
    
    async def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation for the session"""
        try:
            history = await self.get_conversation_history(session_id)
            
            if not history:
                return {"session_id": session_id, "summary": "No conversation history"}
            
            # Count messages by role
            user_messages = [msg for msg in history if msg["role"] == "user"]
            assistant_messages = [msg for msg in history if msg["role"] == "assistant"]
            
            # Get topics/intents from metadata if available
            topics = set()
            for msg in assistant_messages:
                metadata = msg.get("metadata", {})
                if "intent" in metadata:
                    topics.add(metadata["intent"])
            
            # Create summary
            summary = {
                "session_id": session_id,
                "total_messages": len(history),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "topics_discussed": list(topics) if topics else ["general"],
                "first_user_query": user_messages[0]["content"][:100] + "..." if user_messages else None,
                "last_user_query": user_messages[-1]["content"][:100] + "..." if user_messages else None,
                "conversation_active": True
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get conversation summary: {e}")
            return {"session_id": session_id, "error": str(e)}
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (Redis handles TTL, but this can be used for manual cleanup)"""
        try:
            redis_client = await get_redis_client()
            
            # Get all memory keys
            pattern = f"{self.memory_key_prefix}:*"
            keys = await redis_client.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                # Check if key exists and has TTL
                ttl = await redis_client.ttl(key)
                if ttl == -1:  # No TTL set, set one
                    await redis_client.expire(key, self.session_ttl)
                elif ttl == -2:  # Key doesn't exist
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        try:
            redis_client = await get_redis_client()
            
            # Get all memory keys
            pattern = f"{self.memory_key_prefix}:*"
            keys = await redis_client.keys(pattern)
            
            # Extract session IDs
            session_ids = []
            for key in keys:
                if isinstance(key, str):
                    session_id = key.replace(f"{self.memory_key_prefix}:", "")
                    session_ids.append(session_id)
                elif isinstance(key, bytes):
                    session_id = key.decode().replace(f"{self.memory_key_prefix}:", "")
                    session_ids.append(session_id)
            
            logger.debug(f"Found {len(session_ids)} active sessions")
            return session_ids
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    async def export_session_history(self, session_id: str) -> Dict[str, Any]:
        """Export complete session history with metadata"""
        try:
            history = await self.get_conversation_history(session_id)
            session_info = await self.get_session_info(session_id)
            summary = await self.get_conversation_summary(session_id)
            
            export_data = {
                "session_id": session_id,
                "export_timestamp": datetime.now().isoformat(),
                "session_info": session_info,
                "conversation_summary": summary,
                "conversation_history": history,
                "metadata": {
                    "memory_manager_version": "1.0",
                    "max_messages_stored": self.max_messages,
                    "session_ttl": self.session_ttl
                }
            }
            
            logger.info(f"Exported session history for {session_id}")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export session history: {e}")
            return {"session_id": session_id, "error": str(e)}


# Global memory manager instance
memory_manager = MemoryManager()

async def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance"""
    return memory_manager