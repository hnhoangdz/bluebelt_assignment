"""
Authentication service for user management and JWT token handling
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..config import JWT_CONFIG
from ..models.user import User
from ..models.session import Session as UserSession
from ..core.redis_client import RedisClient


class AuthService:
    """Authentication service for user management and JWT token handling"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = JWT_CONFIG["secret_key"]
        self.algorithm = JWT_CONFIG["algorithm"]
        self.access_token_expire_minutes = JWT_CONFIG["access_token_expire_minutes"]
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user
    
    def create_user_session(self, db: Session, user: User, user_agent: str = None, ip_address: str = None) -> UserSession:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=24)  # 24 hour session
        
        session = UserSession(
            id=session_id,
            user_id=user.id,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
            context={},
            state={}
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    def get_user_session(self, db: Session, session_id: str) -> Optional[UserSession]:
        """Get user session by ID"""
        session = db.query(UserSession).filter(
            UserSession.id == session_id,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if session:
            session.update_activity()
            db.commit()
        
        return session
    
    def invalidate_session(self, db: Session, session_id: str) -> bool:
        """Invalidate a user session"""
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.expires_at = datetime.utcnow()
            db.commit()
            return True
        return False
    
    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        payload = self.verify_token(token)
        if payload is None:
            return None
        
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    
    def get_current_user_by_session(self, db: Session, session_id: str) -> Optional[User]:
        """Get current user from session ID (no JWT required)"""
        session = self.get_user_session(db, session_id)
        if not session:
            return None
        
        user = db.query(User).filter(User.id == session.user_id).first()
        return user
    
    async def store_token_in_redis(self, redis_client: RedisClient, user_id: str, token: str) -> bool:
        """Store JWT token in Redis for blacklisting"""
        key = f"token_blacklist:{user_id}"
        expire_time = self.access_token_expire_minutes * 60  # Convert to seconds
        return await redis_client.set(key, token, expire_time)
    
    async def is_token_blacklisted(self, redis_client: RedisClient, user_id: str, token: str) -> bool:
        """Check if token is blacklisted in Redis"""
        key = f"token_blacklist:{user_id}"
        stored_token = await redis_client.get(key)
        return stored_token == token
    
    def register_user(self, db: Session, username: str, email: str, password: str, 
                     first_name: str = None, last_name: str = None) -> Tuple[bool, str, Optional[User]]:
        """Register a new user"""
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return False, "Username already exists", None
        
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            return False, "Email already exists", None
        
        # Create new user
        hashed_password = self.get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            first_name=first_name,
            last_name=last_name,
            is_verified=True,  # Auto-verify for demo
            preferences={},
            settings={}
        )
        
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return True, "User registered successfully", user
        except Exception as e:
            db.rollback()
            return False, f"Registration failed: {str(e)}", None
    
    def update_user_password(self, db: Session, user: User, new_password: str) -> bool:
        """Update user password"""
        try:
            user.password_hash = self.get_password_hash(new_password)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            user_uuid = uuid.UUID(user_id)
            return db.query(User).filter(User.id == user_uuid).first()
        except ValueError:
            return None
    
    def get_user_sessions(self, db: Session, user_id: str, active_only: bool = True) -> list:
        """Get user sessions"""
        try:
            user_uuid = uuid.UUID(user_id)
            query = db.query(UserSession).filter(UserSession.user_id == user_uuid)
            
            if active_only:
                query = query.filter(UserSession.expires_at > datetime.utcnow())
            
            return query.all()
        except ValueError:
            return []