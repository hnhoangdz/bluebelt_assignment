"""
Authentication API routes
"""

from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Header
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.redis_client import get_redis_client
from ..services.auth_service import AuthService
from ..models.user import User
from .schemas import (
    UserLogin, UserRegister, TokenResponse, UserResponse, 
    ErrorResponse, SuccessResponse
)

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_user_by_session(
    x_session_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user by session ID (no JWT required)"""
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID required in X-Session-ID header"
        )
    
    user = auth_service.get_current_user_by_session(db, x_session_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session or session expired"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    return user


@router.post("/register")
async def register_user(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account and return access token
    """
    success, message, user = auth_service.register_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Create access token for the newly registered user
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Create user session
    session = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host
    )
    
    # Update last login
    user.update_last_login()
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer", 
        "expires_in": auth_service.access_token_expire_minutes * 60,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access token
    """
    user = auth_service.authenticate_user(db, user_data.username, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Create user session
    session = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host
    )
    
    # Update last login
    user.update_last_login()
    db.commit()
    
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=auth_service.access_token_expire_minutes * 60
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    """
    Logout user and invalidate session
    """
    # Get session ID from request headers or token
    session_id = request.headers.get("X-Session-ID")
    
    if session_id:
        # Invalidate session
        auth_service.invalidate_session(db, session_id)
        
    
    # Store token in blacklist
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        await auth_service.store_token_in_redis(redis_client, str(current_user.id), token)
    
    return SuccessResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh access token
    """
    # Create new access token
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=auth_service.access_token_expire_minutes * 60
    )


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    # Verify current password
    if not auth_service.verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    success = auth_service.update_user_password(db, current_user, new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    return SuccessResponse(message="Password updated successfully")


@router.get("/sessions", response_model=list)
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's active sessions
    """
    sessions = auth_service.get_user_sessions(db, str(current_user.id), active_only=True)
    return [session.to_dict() for session in sessions]


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def invalidate_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invalidate a specific user session
    """
    # Check if session belongs to current user
    session = auth_service.get_user_session(db, session_id)
    if not session or str(session.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Invalidate session
    success = auth_service.invalidate_session(db, session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate session"
        )
    
    return SuccessResponse(message="Session invalidated successfully")


@router.post("/register-session")
async def register_user_session(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account and return session ID (no JWT)
    """
    success, message, user = auth_service.register_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Create user session
    session = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host
    )
    
    # Update last login
    user.update_last_login()
    db.commit()
    
    return {
        "session_id": session.id,
        "expires_at": session.expires_at.isoformat(),
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    }


@router.post("/login-session")
async def login_user_session(
    user_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return session ID (no JWT)
    """
    user = auth_service.authenticate_user(db, user_data.username, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    
    # Create user session
    session = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host
    )
    
    # Update last login
    user.update_last_login()
    db.commit()
    
    return {
        "session_id": session.id,
        "expires_at": session.expires_at.isoformat(),
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    }


@router.post("/logout-session")
async def logout_user_session(
    request: Request,
    current_user: User = Depends(get_current_user_by_session),
    db: Session = Depends(get_db)
):
    """
    Logout user by session ID (no JWT)
    """
    session_id = request.headers.get("X-Session-ID")
    
    if session_id:
        # Invalidate session
        auth_service.invalidate_session(db, session_id)
    
    return {"message": "Successfully logged out"}


@router.get("/me-session")
async def get_current_user_info_session(current_user: User = Depends(get_current_user_by_session)):
    """
    Get current user information by session (no JWT)
    """
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "avatar_url": current_user.avatar_url,
        "bio": current_user.bio,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }