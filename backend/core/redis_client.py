"""
Redis client for caching and session management
"""

import json
from typing import Optional, Any, Dict
import redis.asyncio as redis
from redis.asyncio import Redis

from ..config import REDIS_CONFIG


class RedisClient:
    """Redis client wrapper with async support"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis"""
        if not self.redis:
            self.redis = redis.from_url(
                REDIS_CONFIG["url"],
                encoding=REDIS_CONFIG["encoding"],
                decode_responses=REDIS_CONFIG["decode_responses"],
                max_connections=REDIS_CONFIG["max_connections"],
            )
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.redis:
            await self.connect()
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set value in Redis"""
        if not self.redis:
            await self.connect()
        return await self.redis.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> int:
        """Delete key from Redis"""
        if not self.redis:
            await self.connect()
        return await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis:
            await self.connect()
        return bool(await self.redis.exists(key))
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        if not self.redis:
            await self.connect()
        return await self.redis.expire(key, seconds)
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from Redis"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(self, key: str, value: Dict[str, Any], expire: Optional[int] = None) -> bool:
        """Set JSON value in Redis"""
        json_value = json.dumps(value)
        return await self.set(key, json_value, expire)
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value"""
        if not self.redis:
            await self.connect()
        return await self.redis.hget(name, key)
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field value"""
        if not self.redis:
            await self.connect()
        return await self.redis.hset(name, key, value)
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields"""
        if not self.redis:
            await self.connect()
        return await self.redis.hgetall(name)
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        if not self.redis:
            await self.connect()
        return await self.redis.hdel(name, *keys)
    
    async def ping(self) -> bool:
        """Ping Redis server"""
        if not self.redis:
            await self.connect()
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False


# Global Redis client instance
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """Get Redis client instance"""
    return redis_client 