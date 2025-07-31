"""
Memory service for Mem0 integration to manage user conversation context and preferences
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MemoryClient = None
    MEM0_AVAILABLE = False

from ..config import MEM0_CONFIG


class MemoryService:
    """Memory service for Mem0 integration to manage user conversation context and preferences"""

    def __init__(self):
        if not MEM0_AVAILABLE:
            self.memory_client = None
            return

        # Initialize MemoryClient with API key
        try:
            if MEM0_CONFIG["api_key"]:
                self.memory_client = MemoryClient(
                    api_key=MEM0_CONFIG["api_key"],
                    org_id=MEM0_CONFIG["org_id"],
                    project_id=MEM0_CONFIG["project_id"]
                )
            else:
                print("Mem0 API key not configured")
                self.memory_client = None
        except Exception as e:
            print(f"Failed to initialize MemoryClient: {e}")
            self.memory_client = None

    async def get_user_memory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user memory from Mem0 using v2 API
        
        Args:
            user_id: User identifier
            
        Returns:
            User memory context or None if not available
        """
        if not self.memory_client:
            return None

        try:
            # Use v2 get memories API with filters
            filters = {
                "user_id": user_id
            }
            memories = self.memory_client.get_all(
                version="v2",
                filters=filters
            )
            return {"memories": memories} if memories else {}
        except Exception as e:
            print(f"Error getting user memory: {e}")
            return None

    async def update_user_memory(
        self, 
        user_id: str, 
        message: str, 
        response: str, 
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Update user memory with new conversation
        
        Args:
            user_id: User identifier
            message: User message
            response: AI response
            context: Additional context
            
        Returns:
            Success status
        """
        if not self.memory_client:
            return False

        try:
            # MemoryClient doesn't have direct update method, use add instead
            messages = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ]

            self.memory_client.add(
                messages=messages,
                user_id=user_id,
                version="v2",
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "context": context or {}
                }
            )

            return True
        except Exception as e:
            print(f"Error updating user memory: {e}")
            return False

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user preferences from memory
        
        Args:
            user_id: User identifier
            
        Returns:
            User preferences or None
        """
        memory = await self.get_user_memory(user_id)
        if memory and "preferences" in memory:
            return memory["preferences"]
        return None

    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences in memory
        
        Args:
            user_id: User identifier
            preferences: User preferences
            
        Returns:
            Success status
        """
        if not self.memory_client:
            return False

        try:
            # Store preferences as a memory entry
            messages = [
                {"role": "user", "content": f"My preferences are: {preferences}"},
                {"role": "assistant", "content": "I've noted your preferences"}
            ]

            self.memory_client.add(
                messages=messages,
                user_id=user_id,
                version="v2",
                metadata={
                    "type": "preferences",
                    "timestamp": datetime.utcnow().isoformat(),
                    "preferences": preferences
                }
            )

            return True
        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False

    async def get_conversation_context(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent conversation context for user using v2 API
        
        Args:
            user_id: User identifier
            limit: Number of recent conversations to retrieve
            
        Returns:
            List of conversation contexts
        """
        if not self.memory_client:
            return []

        try:
            # Use v2 search API with filters
            filters = {
                "user_id": user_id
            }
            results = self.memory_client.search(
                query="conversation", 
                version="v2",
                filters=filters,
                top_k=limit
            )
            return results if results else []
        except Exception as e:
            print(f"Error getting conversation context: {e}")
            return []

    async def add_conversation_context(
        self, 
        user_id: str, 
        conversation: Dict[str, Any]
    ) -> bool:
        """
        Add conversation context to memory
        
        Args:
            user_id: User identifier
            conversation: Conversation data
            
        Returns:
            Success status
        """
        if not self.memory_client:
            return False

        try:
            # Add conversation as memory
            messages = [
                {"role": "user", "content": conversation.get("user_message", "")},
                {"role": "assistant", "content": conversation.get("assistant_response", "")}
            ]

            self.memory_client.add(
                messages=messages,
                user_id=user_id,
                version="v2",
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "conversation_data": conversation
                }
            )

            return True
        except Exception as e:
            print(f"Error adding conversation context: {e}")
            return False

    async def get_user_insights(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user insights and patterns from memory using v2 API
        
        Args:
            user_id: User identifier
            
        Returns:
            User insights or None
        """
        if not self.memory_client:
            return None

        try:
            # Use v2 search API with filters
            filters = {
                "user_id": user_id
            }
            results = self.memory_client.search(
                query="insights preferences behavior", 
                version="v2",
                filters=filters,
                top_k=10
            )
            return {"insights": results} if results else None
        except Exception as e:
            print(f"Error getting user insights: {e}")
            return None

    async def clear_user_memory(self, user_id: str) -> bool:
        """
        Clear user memory
        
        Args:
            user_id: User identifier
            
        Returns:
            Success status
        """
        if not self.memory_client:
            return False

        try:
            # MemoryClient doesn't support direct delete, return False for now
            print(f"Memory deletion not supported in MemoryClient for user {user_id}")
            return False
        except Exception as e:
            print(f"Error clearing user memory: {e}")
            return False

    async def search_memory(self, user_id: str, query: str, session_id: str = None) -> List[Dict[str, Any]]:
        """
        Search user memory for relevant information using v2 API
        
        Args:
            user_id: User identifier
            query: Search query
            session_id: Session identifier (optional)
            
        Returns:
            List of relevant memory entries
        """
        if not self.memory_client:
            return []

        try:
            # Use v2 search API with filters
            filters = {
                "user_id": user_id
            }

            # Add session_id as run_id filter if provided
            if session_id:
                filters = {
                    "AND": [
                        {"user_id": user_id},
                        {"run_id": session_id}
                    ]
                }

            relevant_memories = self.memory_client.search(
                query=query,
                version="v2",
                filters=filters,
                top_k=10
            )
            return relevant_memories if relevant_memories else []
        except Exception as e:
            print(f"Error searching memory: {e}")
            return []

    async def add_memory(
        self, 
        user_id: str, 
        session_id: str, 
        message: str, 
        response: str, 
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Add memory entry with session support
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message: User message
            response: AI response
            context: Additional context
            
        Returns:
            Success status
        """
        if not self.memory_client:
            return True  # Return success for fallback

        try:
            # Add interaction using MemoryClient with message format
            messages = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ]

            self.memory_client.add(
                messages=messages, 
                user_id=user_id, 
                run_id=session_id,  # Use session_id as run_id for session-based memory storage
                version="v2",
                metadata={
                    "session_id": session_id,  # Keep in metadata for additional context
                    "context": context or {}
                }
            )

            return True
        except Exception as e:
            print(f"Error adding memory: {e}")
            return False

    async def get_memory_summary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary of user memory using v2 API
        
        Args:
            user_id: User identifier
            
        Returns:
            Memory summary or None
        """
        if not self.memory_client:
            return None

        try:
            # Use v2 search API with filters
            filters = {
                "user_id": user_id
            }
            results = self.memory_client.search(
                query="summary overview", 
                version="v2",
                filters=filters,
                top_k=5
            )
            return {"summary": results} if results else None
        except Exception as e:
            print(f"Error getting memory summary: {e}")
            return None

    async def close(self):
        """Close memory client if needed"""
        # Mem0 client doesn't need explicit closing
        pass

    def __del__(self):
        """Cleanup on deletion"""
        # No cleanup needed for Mem0 client
        pass 
