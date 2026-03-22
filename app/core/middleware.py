import time
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis_client import redis_client

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window

    async def dispatch(self, request: Request, call_next):
        # 1. Identify client (IP address)
        client_ip = request.client.host
        route = request.url.path
        key = f"rate_limit:{client_ip}:{route}"

        # 2. Get current count from Redis
        current_count = await redis_client.get_cache(key)
        count = int(current_count) if current_count else 0

        if count >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later."
            )

        # 3. Increment count
        if count == 0:
            await redis_client.set_cache(key, 1, ttl=self.window)
        else:
            # Simple increment logic assuming Redis backend
            await redis_client.set_cache(key, count + 1, ttl=self.window)

        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
