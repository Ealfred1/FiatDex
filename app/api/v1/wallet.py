from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.redis_client import redis_client
from app.models.user import User
from app.schemas.wallet import (
    WalletAuthRequest, WalletNonceResponse, WalletVerifyRequest, 
    TokenResponse, UserResponse, WalletBalance
)
from app.services.auth_service import auth_service
from app.services.injective_service import injective_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/wallet", tags=["Wallet"])

@router.post("/auth/nonce", response_model=WalletNonceResponse)
async def get_nonce(request: WalletAuthRequest):
    """
    Generate a nonce for wallet signature authentication.
    """
    nonce = str(uuid.uuid4())
    message = auth_service.generate_sign_message(request.wallet_address, nonce)
    
    # Store nonce in Redis for 5 minutes
    await redis_client.set_cache(f"nonce:{request.wallet_address}", nonce, ttl=300)
    
    return WalletNonceResponse(nonce=nonce, message=message)

@router.post("/auth/verify", response_model=TokenResponse)
async def verify_signature(request: WalletVerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Verify wallet signature and issue JWT access token.
    """
    message = auth_service.generate_sign_message(request.wallet_address, request.nonce)
    is_valid = await auth_service.verify_signature(
        request.wallet_address, 
        request.wallet_type, 
        request.signature, 
        message, 
        request.nonce
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid signature or nonce"
        )
    
    # Check if user exists, or create new one
    stmt = select(User).where(User.wallet_address == request.wallet_address)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            wallet_address=request.wallet_address,
            wallet_type=request.wallet_type
        )
        db.add(user)
        await db.commit()
    
    # Update last active
    user.last_active = datetime.utcnow()
    await db.commit()
    
    # Issue JWT
    access_token = auth_service.create_access_token(data={"sub": user.wallet_address})
    
    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    """
    return UserResponse(
        wallet_address=current_user.wallet_address,
        wallet_type=current_user.wallet_type,
        preferred_currency=current_user.preferred_currency,
        is_active=current_user.is_active
    )

@router.get("/balance", response_model=WalletBalance)
async def get_balance(current_user: User = Depends(get_current_user)):
    """
    Fetch live wallet balances for the authenticated user.
    """
    balances = await injective_service.get_wallet_balances(current_user.wallet_address)
    
    # Calculate total value (mock for now)
    total_val = sum(b.balance_usd for b in balances)
    
    return WalletBalance(
        total_value_usd=total_val,
        total_value_local=total_val * 1, # Placeholder for conversion
        local_currency=current_user.preferred_currency,
        tokens=balances
    )

@router.put("/preferences", response_model=UserResponse)
async def update_preferences(
    currency: Optional[str] = None,
    push_token: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user preferences like local currency or push notification token.
    """
    if currency:
        current_user.preferred_currency = currency
    if push_token:
        current_user.expo_push_token = push_token
        
    await db.commit()
    return UserResponse(
        wallet_address=current_user.wallet_address,
        wallet_type=current_user.wallet_type,
        preferred_currency=current_user.preferred_currency,
        is_active=current_user.is_active
    )
