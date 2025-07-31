"""
User model for authentication and profile management
"""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class User(Base):
    """User model for authentication and profile management"""
    
    __tablename__ = "users"
    __table_args__ = {"schema": "dextrends"}
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication fields
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Status fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Preferences and settings
    preferences = Column(JSON, default={}, nullable=False)
    settings = Column(JSON, default={}, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Additional fields
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.username
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated and active"""
        return self.is_active and self.is_verified
    
    def update_last_login(self) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference by key"""
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set user preference"""
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary"""
        data = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
        
        if include_sensitive:
            data.update({
                "preferences": self.preferences,
                "settings": self.settings,
            })
        
        return data 