"""
Main FastAPI application for Dextrends AI Chatbot
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings
from .core.database import init_db, close_db
from .core.redis_client import get_redis_client

# Import routers
from .api.auth import router as auth_router
from .api.chat import router as chat_router
from .api.user import router as user_router
from .api.rag_demo import router as rag_demo_router

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting Dextrends AI Chatbot...")
    init_db()  # Initialize database
    
    # Test Redis connection
    redis_client = await get_redis_client()
    await redis_client.connect()
    redis_status = await redis_client.ping()
    print(f"Redis connection: {'OK' if redis_status else 'FAILED'}")
    
    yield
    
    # Shutdown
    print("Shutting down Dextrends AI Chatbot...")
    await redis_client.disconnect()
    close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Chatbot API for Dextrends - Digital Financial Services and Blockchain Solutions",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


# Include API routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
# Add chat router also at /api/chat for frontend compatibility
app.include_router(chat_router, prefix="/api/chat", tags=["Chat (Legacy)"])
app.include_router(user_router, prefix="/api/user", tags=["User"])
app.include_router(rag_demo_router, prefix="/api/v1", tags=["RAG Demo"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Dextrends AI Chatbot API",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "environment": settings.environment
    }

# Test endpoint
@app.post("/test-chat", tags=["Test"])
async def test_chat_simple():
    """Simple test for chat functionality"""
    try:
        from .services.memory_service import MemoryService
        from openai import OpenAI
        from .config import OPENAI_CONFIG
        
        # Test OpenAI
        client = OpenAI(api_key=OPENAI_CONFIG["api_key"])
        response = client.chat.completions.create(
            model=OPENAI_CONFIG["model"],
            messages=[{"role": "user", "content": "Hello, just say hi back"}],
            max_tokens=10
        )
        
        # Test Mem0
        memory_service = MemoryService()
        results = await memory_service.search_memory("test123", "hello", "session123")
        
        return {
            "openai_response": response.choices[0].message.content,
            "memory_results": results,
            "status": "success"
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
