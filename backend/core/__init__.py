"""
Core functionality for Dextrends AI Chatbot
"""

from .database import get_db, get_engine, init_db, close_db
from .redis_client import get_redis_client

__all__ = ["get_db", "get_engine", "init_db", "close_db", "get_redis_client"] 