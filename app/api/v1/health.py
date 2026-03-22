from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import datetime
from app.core.database import get_db
from app.core.redis_client import redis_client
from app.services.injective_service import injective_service
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])

@router.get(
    "/health",
    summary="API health check",
    description="""
Returns the health status of all FiatDex backend dependencies.

Checks:
- **API:** Always returns ok if this endpoint responds
- **Database:** Tests async DB connection with a simple SELECT 1
- **Redis:** Tests Redis PING
- **Injective API:** Tests connectivity to Injective Exchange API

Used by deployment platforms (Railway, Render) for uptime monitoring.
Returns HTTP 200 if all healthy, HTTP 503 if any dependency is down.
    """,
    response_model=HealthResponse,
    responses={
        200: {"description": "All systems healthy"},
        503: {"description": "One or more dependencies unhealthy"},
    },
)
async def health_check(response: Response, db: AsyncSession = Depends(get_db)):
    checks = {
        "database": "ok",
        "redis": "ok",
        "injective": "ok"
    }
    
    # 1. Check Database
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "error"
        
    # 2. Check Redis
    try:
        await redis_client.client.ping()
    except Exception:
        checks["redis"] = "error"
        
    # 3. Check Injective Node
    try:
        await injective_service.client.get_spot_markets(status="active")
    except Exception:
        checks["injective"] = "error"
        
    status_code = status.HTTP_200_OK
    overall_status = "healthy"
    
    if any(v == "error" for v in checks.values()):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "degraded"
        response.status_code = status_code
        
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        checks=checks,
        version="1.0.0"
    )
