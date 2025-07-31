"""
API request and response schemas for the chat API
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Request schema for chat messages"""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier") 
    query: str = Field(..., description="User query/message")


class ChatResponse(BaseModel):
    """Response schema for chat API"""
    response: str = Field(..., description="AI assistant response")
    conversation_id: str = Field(..., description="Conversation identifier")
    sources: Optional[List[Dict[str, Any]]] = Field(default=[], description="Source documents from knowledge base")
    context_used: Optional[Dict[str, Any]] = Field(default={}, description="Context information used")
    routing_info: Optional[Dict[str, Any]] = Field(default={}, description="Query routing information") 
    tokens_used: Optional[int] = Field(default=0, description="Total tokens used")
    response_time_ms: Optional[int] = Field(default=0, description="Response time in milliseconds")
    model_used: Optional[str] = Field(default="", description="AI model used")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class ConversationItem(BaseModel):
    """Individual conversation item"""
    id: str
    message: str
    response: str
    timestamp: datetime
    tokens_used: Optional[int] = 0
    response_time_ms: Optional[int] = 0
    is_error: bool = False


class ConversationHistory(BaseModel):
    """Conversation history response"""
    conversations: List[ConversationItem]
    total_count: int


class SessionInfo(BaseModel):
    """Session information"""
    id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_active: bool


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    """Success response schema"""
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=100)


class MemorySearchRequest(BaseModel):
    """Memory search request schema"""
    query: str = Field(..., description="Search query")
    session_id: Optional[str] = Field(default=None, description="Session ID for filtering")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")


class MemorySearchResponse(BaseModel):
    """Memory search response schema"""
    user_id: str
    query: str
    session_id: Optional[str] = None
    results: List[Dict[str, Any]]
    total_count: int


class UserLogin(BaseModel):
    """User login request schema"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserRegister(BaseModel):
    """User registration request schema"""
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")
    first_name: Optional[str] = Field(default=None, description="First name")
    last_name: Optional[str] = Field(default=None, description="Last name")


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str = Field(..., description="Access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserResponse(BaseModel):
    """User response schema"""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(default=None, description="Full name")
    first_name: Optional[str] = Field(default=None, description="First name")
    last_name: Optional[str] = Field(default=None, description="Last name")
    is_active: bool = Field(..., description="Is user active")
    is_verified: bool = Field(..., description="Is user verified")
    avatar_url: Optional[str] = Field(default=None, description="Avatar URL")
    bio: Optional[str] = Field(default=None, description="User bio")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")