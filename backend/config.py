"""
Configuration module for Dextrends AI Chatbot
Handles environment variables and application settings
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "Dextrends AI Chatbot"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(env="REDIS_URL")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = "gpt-4.1-nano"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.7
    
    # Mem0
    mem0_api_key: Optional[str] = Field(default=None, env="MEM0_API_KEY")
    mem0_org_id: Optional[str] = Field(default=None, env="MEM0_ORG_ID")
    mem0_project_id: Optional[str] = Field(default=None, env="MEM0_PROJECT_ID")
    mem0_base_url: str = "https://api.mem0.ai"
    
    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields instead of raising validation errors


# Global settings instance
settings = Settings()


# Database configuration
DATABASE_CONFIG = {
    "url": settings.database_url,
    "echo": settings.debug,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

# Redis configuration
REDIS_CONFIG = {
    "url": settings.redis_url,
    "encoding": "utf-8",
    "decode_responses": True,
    "max_connections": 20,
}

# OpenAI configuration
OPENAI_CONFIG = {
    "api_key": settings.openai_api_key,
    "model": settings.openai_model,
    "max_tokens": settings.openai_max_tokens,
    "temperature": settings.openai_temperature,
}

# Mem0 configuration
MEM0_CONFIG = {
    "api_key": settings.mem0_api_key,
    "org_id": settings.mem0_org_id,
    "project_id": settings.mem0_project_id,
    "base_url": settings.mem0_base_url,
}

# Qdrant configuration
QDRANT_CONFIG = {
    "url": settings.qdrant_url,
    "api_key": settings.qdrant_api_key,
}

# JWT configuration
JWT_CONFIG = {
    "secret_key": settings.secret_key,
    "algorithm": settings.algorithm,
    "access_token_expire_minutes": settings.access_token_expire_minutes,
}
