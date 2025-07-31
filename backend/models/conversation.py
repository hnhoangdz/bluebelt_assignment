"""
Conversation model for storing chat messages and AI responses
"""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Conversation(Base):
    """Conversation model for storing chat messages and AI responses"""
    
    __tablename__ = "conversations"
    __table_args__ = {"schema": "dextrends"}
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("dextrends.users.id"), nullable=False, index=True)
    session_id = Column(String(255), ForeignKey("dextrends.sessions.id"), nullable=False, index=True)
    
    # Message content
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    
    # Message metadata
    message_type = Column(String(50), default="text", nullable=False)  # text, image, file, etc.
    response_type = Column(String(50), default="text", nullable=False)
    
    # AI processing metadata
    tokens_used = Column(Integer, default=0, nullable=False)
    response_time_ms = Column(Integer, default=0, nullable=False)
    model_used = Column(String(100), nullable=True)
    
    # Context and metadata
    context = Column(JSON, default={}, nullable=False)
    conversation_metadata = Column(JSON, default={}, nullable=False)
    
    # Status and flags
    is_error = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="conversations")
    session = relationship("Session", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, session_id='{self.session_id}')>"
    
    @property
    def is_successful(self) -> bool:
        """Check if conversation was successful"""
        return not self.is_error
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value by key"""
        return self.context.get(key, default)
    
    def set_context(self, key: str, value: Any) -> None:
        """Set context value"""
        if not self.context:
            self.context = {}
        self.context[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key"""
        return self.conversation_metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        if not self.conversation_metadata:
            self.conversation_metadata = {}
        self.conversation_metadata[key] = value
    
    def set_error(self, error_message: str) -> None:
        """Set conversation as error"""
        self.is_error = True
        self.error_message = error_message
    
    def set_success(self, tokens_used: int = 0, response_time_ms: int = 0, model_used: str = None) -> None:
        """Set conversation as successful with metadata"""
        self.is_error = False
        self.error_message = None
        self.tokens_used = tokens_used
        self.response_time_ms = response_time_ms
        if model_used:
            self.model_used = model_used
    
    def to_dict(self) -> dict:
        """Convert conversation to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": self.session_id,
            "message": self.message,
            "response": self.response,
            "message_type": self.message_type,
            "response_type": self.response_type,
            "tokens_used": self.tokens_used,
            "response_time_ms": self.response_time_ms,
            "model_used": self.model_used,
            "context": self.context,
            "metadata": self.conversation_metadata,
            "is_error": self.is_error,
            "error_message": self.error_message,
            "is_successful": self.is_successful,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        } 