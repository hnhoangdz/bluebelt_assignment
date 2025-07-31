"""
Database connection and session management
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..config import DATABASE_CONFIG
from ..models.base import Base

# Global engine and session factory variables
engine = None
SessionLocal = None


def get_engine():
    """Get or create database engine"""
    global engine
    if engine is None:
        engine = create_engine(
            DATABASE_CONFIG["url"],
            echo=DATABASE_CONFIG["echo"],
            pool_size=DATABASE_CONFIG["pool_size"],
            max_overflow=DATABASE_CONFIG["max_overflow"],
            pool_pre_ping=DATABASE_CONFIG["pool_pre_ping"],
            pool_recycle=DATABASE_CONFIG["pool_recycle"],
            poolclass=StaticPool if DATABASE_CONFIG["url"].startswith("sqlite") else None,
        )
    return engine


def get_session_local():
    """Get or create session factory"""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI
    Yields a database session
    """
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables and schema
    """
    db_engine = get_engine()
    
    # Create schema if it doesn't exist (PostgreSQL only)
    if not DATABASE_CONFIG["url"].startswith("sqlite"):
        with db_engine.connect() as conn:
            # Create schema if it doesn't exist
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS dextrends"))
            # Set search path for this session
            conn.execute(text("SET search_path TO dextrends, public"))
            conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=db_engine)


def close_db() -> None:
    """
    Close database connections
    """
    global engine
    if engine is not None:
        engine.dispose()
        engine = None 