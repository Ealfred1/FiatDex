from fastapi import Depends
from app.services.auth_service import auth_service
from app.core.database import get_db
from app.core.redis_client import get_redis

# Shared dependencies for FastAPI routes
get_current_user = auth_service.get_current_user
