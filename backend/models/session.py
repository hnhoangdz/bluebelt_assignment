"""
Session model for managing user sessions and conversation context
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Session(Base):
    """Session model for managing user sessions and conversation context"""
    
    __tablename__ = "sessions"
    __table_args__ = {"schema": "dextrends"}
    
    # Primary key
    id = Column(String(255), primary_key=True)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("dextrends.users.id"), nullable=False, index=True)
    
    # Session metadata
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Context and state
    context = Column(JSON, default={}, nullable=False)
    state = Column(JSON, default={}, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("User", backref="sessions")
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(id='{self.id}', user_id={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if session is active and not expired"""
        return not self.is_expired
    
    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def extend_session(self, hours: int = 1) -> None:
        """Extend session expiration time"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value by key"""
        return self.context.get(key, default)
    
    def set_context(self, key: str, value: Any) -> None:
        """Set context value"""
        if not self.context:
            self.context = {}
        self.context[key] = value
    
    def update_context(self, data: dict) -> None:
        """Update context with new data"""
        if not self.context:
            self.context = {}
        self.context.update(data)
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value by key"""
        return self.state.get(key, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """Set state value"""
        if not self.state:
            self.state = {}
        self.state[key] = value
    
    def clear_context(self) -> None:
        """Clear session context"""
        self.context = {}
    
    def clear_state(self) -> None:
        """Clear session state"""
        self.state = {}
    
    def to_dict(self) -> dict:
        """Convert session to dictionary"""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "context": self.context,
            "state": self.state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "is_active": self.is_active,
        } 