"""
Redis client — shared across services.

Usage:
    from shared.redis_client import get_redis

    redis = await get_redis()
    await redis.setex(f"otp:{phone}", 300, "123456")
    otp = await redis.get(f"otp:{phone}")
"""

import redis.asyncio as aioredis
from shared.config import settings

_redis_client: aioredis.Redis | None = None


class MockRedis:
    def __init__(self):
        self.data = {}
    async def set(self, key, value, ex=None):
        self.data[key] = value
    async def setex(self, key, time, value):
        self.data[key] = value
    async def get(self, key):
        return self.data.get(key)
    async def delete(self, key):
        self.data.pop(key, None)
    async def ping(self):
        return True
    async def close(self):
        pass

async def get_redis():
    """Get or create async Redis client."""
    global _redis_client
    if _redis_client is None:
        if "sqlite" in settings.DATABASE_URL:
            _redis_client = MockRedis()
        else:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
    return _redis_client


async def close_redis():
    """Close Redis connection on app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
