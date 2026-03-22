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

@router.post(
    "/auth/nonce", 
    summary="Request authentication nonce",
    description="""
Step 1 of 2 in the non-custodial wallet authentication flow.

Returns a unique nonce and a pre-formatted message for the user to sign
with their wallet (Keplr or MetaMask).

**Why sign a message?**
FiatDex is non-custodial — it never holds private keys. Instead of a password,
users prove they own their wallet by signing a challenge message.
The signature is then verified server-side in Step 2.

**Nonce expiry:** 5 minutes. Request a fresh nonce if expired.

**Example message returned:**
```
FiatDex Authentication
Address: inj1abc...xyz
Nonce: a3f92bc1
Timestamp: 2026-03-22T10:00:00Z
```
Sign this exact string in your wallet.
""",
    response_model=WalletNonceResponse,
    operation_id="request_auth_nonce",
)
async def get_nonce(request: WalletAuthRequest):
    nonce = str(uuid.uuid4())
    message = auth_service.generate_sign_message(request.wallet_address, nonce)
    
    # Store nonce in Redis for 5 minutes
    await redis_client.set_cache(f"nonce:{request.wallet_address}", nonce, ttl=300)
    
    return WalletNonceResponse(nonce=nonce, message=message, expires_in=300)

@router.post(
    "/auth/verify", 
    summary="Verify wallet signature and get JWT",
    description="""
Step 2 of 2 in the wallet authentication flow.

Submits the signed message from the user's wallet. FiatDex verifies the
signature cryptographically:
- **Keplr (Cosmos):** secp256k1 signature verification
- **MetaMask (EVM):** eth_account personal_sign recovery

On success:
- Creates a user account if this is the first login
- Returns a JWT Bearer token (valid 7 days)
- Returns the user profile

**Use the returned `access_token` as a Bearer token on all authenticated endpoints:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```
""",
    response_model=TokenResponse,
    operation_id="verify_wallet_signature",
)
async def verify_signature(request: WalletVerifyRequest, db: AsyncSession = Depends(get_db)):
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
    
    return TokenResponse(access_token=access_token, user=user)

@router.get(
    "/balance", 
    summary="Get wallet token balances",
    description="""
Returns all token balances held in the authenticated user's connected wallet,
enriched with current USD and local currency values.

Data sourced live from the Injective Bank module — always reflects on-chain state.

Each balance includes:
- Token symbol, name, and logo
- Raw balance (in token's native decimals)
- Formatted balance (human-readable)
- Current USD value
- Current local currency value (based on user's `preferred_currency`)
""",
    response_model=WalletBalance,
    operation_id="get_wallet_balance",
)
async def get_balance(current_user: User = Depends(get_current_user)):
    balances = await injective_service.get_wallet_balances(current_user.wallet_address)
    
    # Calculate total value (mock for now)
    total_val = sum(b.balance_usd for b in balances)
    
    return WalletBalance(
        total_value_usd=total_val,
        total_value_local=total_val * 1, # Placeholder for conversion
        local_currency=current_user.preferred_currency,
        tokens=balances
    )

@router.put(
    "/preferences", 
    response_model=UserResponse,
    operation_id="update_user_preferences",
)
async def update_preferences(
    currency: Optional[str] = Query(None, pattern="^(NGN|GHS|KES|ZAR|USD)$"),
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
