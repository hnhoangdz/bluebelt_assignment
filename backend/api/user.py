"""
User API routes
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/stats")
async def get_user_stats():
    """
    Get user statistics (simplified for demo)
    """
    # For demo purposes, return mock user stats
    # In production, this would require authentication and fetch real stats
    return {
        "total_conversations": 0,
        "total_tokens": 0,
        "total_messages": 0,
        "last_activity": None
    }