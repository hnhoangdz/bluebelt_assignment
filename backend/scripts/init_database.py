#!/usr/bin/env python3
"""
Database initialization script for Dextrends AI Chatbot
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.database import engine, init_db
from models import User, Session, Conversation
from config import settings


def create_schema():
    """Create the dextrends schema"""
    print("Creating dextrends schema...")
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS dextrends"))
        conn.execute(text("SET search_path TO dextrends, public"))
        conn.commit()
    print("✅ Schema created successfully")


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    init_db()
    print("✅ Tables created successfully")


def create_indexes():
    """Create additional indexes for better performance"""
    print("Creating database indexes...")
    with engine.connect() as conn:
        # Users table indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON dextrends.users(username)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON dextrends.users(email)"))
        
        # Sessions table indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON dextrends.sessions(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON dextrends.sessions(expires_at)"))
        
        # Conversations table indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON dextrends.conversations(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON dextrends.conversations(session_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON dextrends.conversations(timestamp)"))
        
        
        conn.commit()
    print("✅ Indexes created successfully")


def create_functions():
    """Create database functions"""
    print("Creating database functions...")
    with engine.connect() as conn:
        # Function to update updated_at timestamp
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION dextrends.update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """))
        
        # Function to clean expired sessions
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION dextrends.clean_expired_sessions()
            RETURNS INTEGER AS $$
            DECLARE
                deleted_count INTEGER;
            BEGIN
                DELETE FROM dextrends.sessions WHERE expires_at < CURRENT_TIMESTAMP;
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                RETURN deleted_count;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        conn.commit()
    print("✅ Functions created successfully")


def create_triggers():
    """Create database triggers"""
    print("Creating database triggers...")
    with engine.connect() as conn:
        # Trigger for users table
        conn.execute(text("""
            DROP TRIGGER IF EXISTS update_users_updated_at ON dextrends.users;
            CREATE TRIGGER update_users_updated_at 
                BEFORE UPDATE ON dextrends.users 
                FOR EACH ROW 
                EXECUTE FUNCTION dextrends.update_updated_at_column();
        """))
        
        conn.commit()
    print("✅ Triggers created successfully")


def insert_sample_data():
    """Insert sample data for testing"""
    print("Inserting sample data...")
    from sqlalchemy.orm import sessionmaker
    from passlib.context import CryptContext
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create password context
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@dextrends.com",
                password_hash=pwd_context.hash("admin123"),
                first_name="Admin",
                last_name="User",
                is_active=True,
                is_verified=True
            )
            db.add(admin_user)
            print("✅ Admin user created")
        
        # Check if demo user already exists
        demo_user = db.query(User).filter(User.username == "demo_user").first()
        if not demo_user:
            # Create demo user
            demo_user = User(
                username="demo_user",
                email="demo@dextrends.com",
                password_hash=pwd_context.hash("demo123"),
                first_name="Demo",
                last_name="User",
                is_active=True,
                is_verified=True
            )
            db.add(demo_user)
            print("✅ Demo user created")
        
        db.commit()
        print("✅ Sample data inserted successfully")
        
    except Exception as e:
        print(f"❌ Error inserting sample data: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function"""
    print("🚀 Initializing Dextrends AI Chatbot Database")
    print("=" * 50)
    print(f"📊 Connecting to PostgreSQL at: {settings.database_url}")
    
    try:
        # Test database connection
        print("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version}")
        
        # Create schema
        create_schema()
        
        # Create tables
        create_tables()
        
        # Create indexes
        create_indexes()
        
        # Create functions
        create_functions()
        
        # Create triggers
        create_triggers()
        
        # Insert sample data
        insert_sample_data()
        
        print("\n" + "=" * 50)
        print("🎉 Database initialization completed successfully!")
        print("\nSample users created:")
        print("- Username: admin, Password: admin123")
        print("- Username: demo_user, Password: demo123")
        print(f"\nDatabase URL: {settings.database_url}")
        
    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        print(f"Make sure PostgreSQL is running on port 8432 and accessible")
        sys.exit(1)


if __name__ == "__main__":
    main() 