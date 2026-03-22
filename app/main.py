from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.database import engine
from app.core.redis_client import redis_client
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections
    yield
    # Shutdown: Close connections
    await redis_client.close()
    await engine.dispose()

from app.api.v1.router import api_router

app = FastAPI(
    title="FiatDex API",
    description="FiatDex — Mobile-first DEX explorer and fiat onramp on Injective",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# v1 Routes
app.include_router(api_router, prefix="/api/v1")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
app.add_middleware(RateLimitMiddleware, limit=60, window=60)
app.add_middleware(SecurityHeadersMiddleware)

# Exception Handlers
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.core.exceptions import (
    global_exception_handler, 
    validation_exception_handler, 
    sqlalchemy_exception_handler,
    FiatDexException,
    fiatdex_exception_handler
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(FiatDexException, fiatdex_exception_handler)

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

@app.get("/")
async def root():
    return {"message": "Welcome to FiatDex API — Injective Africa Buildathon 2026"}
