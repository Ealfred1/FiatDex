import redis.asyncio as redis
from app.config import settings
import json
from typing import Any, Optional

class RedisClient:
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10
        )

    async def get_cache(self, key: str) -> Optional[Any]:
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set_cache(self, key: str, value: Any, ttl: int = 60) -> bool:
        if not isinstance(value, str):
            value = json.dumps(value)
        return await self.client.set(key, value, ex=ttl)

    async def delete_cache(self, key: str) -> int:
        return await self.client.delete(key)

    async def close(self):
        await self.client.close()

redis_client = RedisClient()

async def get_redis():
    """FastAPI dependency for Redis client."""
    return redis_client
