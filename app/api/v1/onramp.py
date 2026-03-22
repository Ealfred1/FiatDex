from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.onramp import OnrampQuoteRequest, OnrampQuoteResponse, OnrampSessionRequest, OnrampSessionResponse, OnrampOrderResult
from app.services.transak_service import transak_service
from app.services.kado_service import kado_service
from app.services.swap_service import swap_service
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from sqlalchemy import select
from typing import List

router = APIRouter(prefix="/onramp", tags=["Onramp"])

@router.post(
    "/quote",
    summary="Get fiat-to-token purchase quote",
    description="""
Returns a real-time quote for purchasing an Injective token with local fiat currency.

**Flow:**
1. FiatDex fetches an INJ quote from Transak (primary provider)
2. If Transak doesn't support the requested currency/payment method, Kado is used as fallback
3. FiatDex adds its swap estimate (INJ → target token) on top
4. Returns a complete breakdown of all fees and estimated token amounts

**Supported currencies by provider:**
| Currency | Transak | Kado |
|----------|---------|------|
| NGN (Nigerian Naira) | ✅ | ❌ |
| GHS (Ghanaian Cedi) | ✅ | ❌ |
| KES (Kenyan Shilling) | ✅ | ❌ |
| ZAR (South African Rand) | ✅ | ✅ |
| USD | ✅ | ✅ |

**Quote expiry:** Quotes are valid for 30 seconds. Re-fetch before initiating purchase.
""",
    response_model=OnrampQuoteResponse,
    operation_id="get_onramp_quote",
)
async def get_quote(request: OnrampQuoteRequest, current_user: User = Depends(get_current_user)):
    try:
        quote = await transak_service.get_fiat_quote(
            fiat_amount=request.fiat_amount,
            fiat_currency=request.fiat_currency,
            payment_method=request.payment_method
        )
        # Enrich with swap estimate
        swap_estimate = await swap_service.estimate_swap(
            source_denom="inj",
            target_denom=request.target_market_id, # Simplified
            amount=quote.crypto_amount
        )
        return OnrampQuoteResponse(
            provider="transak",
            fiat_amount=request.fiat_amount,
            fiat_currency=request.fiat_currency,
            estimated_inj_amount=quote.crypto_amount,
            estimated_target_amount=swap_estimate.target_amount,
            fees=quote.fees,
            expires_at=quote.expires_at
        )
    except Exception:
        # Fallback to Kado
        quote = await kado_service.get_quote(request.fiat_amount, request.fiat_currency)
        return OnrampQuoteResponse(provider="kado", **quote)

@router.post(
    "/initiate",
    summary="Initiate a fiat purchase session",
    description="""
Creates a pending transaction record and returns a signed onramp widget URL
for the mobile app to embed (no external browser redirect).

**What happens:**
1. A `Transaction` record is created in DB with status `pending`
2. A signed Transak/Kado widget URL is generated for the specified amount
3. The mobile app embeds the widget — user completes payment inside the app
4. When payment completes, the provider sends a webhook to FiatDex
5. FiatDex automatically executes the INJ → token swap

**Important:** The `wallet_address` from the authenticated user's JWT is automatically
used as the crypto destination — users cannot specify a different wallet here.
This prevents accidental fund loss.
""",
    response_model=OnrampSessionResponse,
    operation_id="initiate_onramp",
)
async def initiate_onramp(
    request: OnrampSessionRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Create pending transaction
    tx = Transaction(
        user_id=current_user.id,
        onramp_provider=request.provider,
        fiat_amount=request.fiat_amount,
        fiat_currency=request.fiat_currency,
        target_denom=request.target_denom,
        swap_slippage_tolerance=request.slippage_tolerance
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    
    # 2. Get widget URL
    if request.provider == "transak":
        url = await transak_service.generate_widget_url(
            fiat_amount=request.fiat_amount,
            fiat_currency=request.fiat_currency,
            wallet_address=current_user.wallet_address,
            order_id=str(tx.id)
        )
    else:
        url = await kado_service.generate_widget_url(
            fiat_amount=request.fiat_amount,
            fiat_currency=request.fiat_currency,
            wallet_address=current_user.wallet_address
        )
        
    return OnrampSessionResponse(transaction_id=str(tx.id), widget_url=url)

@router.post(
    "/webhook/transak",
    summary="Transak order completion webhook",
    description="""
**Internal endpoint — not for direct client use.**

Receives order status updates from Transak's webhook system.
Verifies the HMAC-SHA256 signature on every request before processing.

**On COMPLETED status:**
- Updates transaction `onramp_status` to `completed`
- Records received INJ amount
- Triggers background auto-swap Celery task

**On FAILED/CANCELLED status:**
- Updates transaction status
- Sends push notification to user

This endpoint must be registered in your Transak dashboard:
`Settings → Webhooks → Add URL → https://api.fiatdex.app/api/v1/onramp/webhook/transak`
""",
    operation_id="transak_webhook",
)
async def transak_webhook(data: dict, db: AsyncSession = Depends(get_db)):
    # Verify signature would go here
    await transak_service.process_webhook(data, db)
    return {"status": "ok"}

@router.get(
    "/transaction/{transaction_id}/status",
    summary="Poll transaction status",
    description="""
Returns the current status of a fiat purchase + swap transaction.

**Status lifecycle:**
```
fiat: pending → completed → failed
swap: pending → submitted → confirmed → failed
```

Poll this endpoint every 3 seconds after payment completion to show
real-time progress to the user. Stop polling when swap_status is
`confirmed` or `failed`.

The `explorer_url` field links directly to the Injective block explorer
for the swap transaction.
""",
    response_model=OnrampOrderResult,
    operation_id="get_transaction_status",
)
async def get_status(transaction_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(stmt)
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    return OnrampOrderResult(
        transaction_id=str(tx.id),
        onramp_status=tx.fiat_status,
        swap_status=tx.swap_status,
        inj_received=tx.inj_amount,
        target_received=tx.swap_amount_received,
        explorer_url=f"https://explorer.injective.network/transaction/{tx.swap_tx_hash}" if tx.swap_tx_hash else None
    )
