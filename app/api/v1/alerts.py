from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.alert import PriceAlert
from app.models.watchlist import WatchlistItem
from app.schemas.alert import AlertCreate, AlertResponse, WatchlistAddItem, WatchlistResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post(
    "",
    summary="Create price alert",
    description="""
Creates a price alert that sends a push notification when a token
reaches the specified price threshold.

**Conditions:**
- `above` — Alert when token price rises above `target_price_usd`
- `below` — Alert when token price falls below `target_price_usd`

**Delivery:** Push notification via Expo. Requires `expo_push_token`
to be set on the user profile (`PUT /api/v1/wallet/preferences`).

Alerts are checked every 60 seconds against the cached price feed.
Triggered alerts are automatically deactivated after firing.

**Limit:** 10 active alerts per user (enforced server-side).
""",
    response_model=AlertResponse,
    operation_id="create_price_alert",
)
async def create_alert(
    alert: AlertCreate, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check limit
    count_stmt = select(PriceAlert).where(PriceAlert.user_id == current_user.id, PriceAlert.is_active == True)
    result = await db.execute(count_stmt)
    if len(result.scalars().all()) >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 active alerts allowed")

    new_alert = PriceAlert(
        user_id=current_user.id,
        token_denom=alert.token_denom,
        token_symbol=alert.token_symbol,
        target_price_usd=alert.target_price_usd,
        condition=alert.condition
    )
    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)
    return new_alert

@router.get(
    "/watchlist",
    summary="Get watchlist tokens",
    description="""
Returns all tokens the user has saved to their watchlist.

Watchlist tokens are displayed prominently in the app's home screen
and receive new listing notifications when the feature is enabled.

No price alerts are set by watchlisting — use `POST /api/v1/alerts`
to add a price condition on top.
""",
    response_model=List[WatchlistResponse],
    operation_id="get_watchlist",
)
async def get_watchlist(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(WatchlistItem).where(WatchlistItem.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/watchlist", response_model=WatchlistResponse)
async def add_to_watchlist(
    item: WatchlistAddItem,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_item = WatchlistItem(
        user_id=current_user.id,
        token_denom=item.token_denom,
        token_symbol=item.token_symbol
    )
    db.add(new_item)
    try:
        await db.commit()
    except Exception:
        raise HTTPException(status_code=409, detail="Token already in watchlist")
    await db.refresh(new_item)
    return new_item

@router.delete("/watchlist/{token_denom}")
async def remove_from_watchlist(
    token_denom: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = delete(WatchlistItem).where(
        WatchlistItem.user_id == current_user.id,
        WatchlistItem.token_denom == token_denom
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}
