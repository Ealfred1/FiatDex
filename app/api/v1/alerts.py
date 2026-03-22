from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.alert import PriceAlert
from app.models.watchlist import WatchlistItem
from app.schemas.alert import (
    PriceAlertCreate, PriceAlertResponse, WatchlistCreate, WatchlistItemResponse
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("", response_model=PriceAlertResponse)
async def create_alert(
    alert_in: PriceAlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new price alert.
    """
    new_alert = PriceAlert(
        user_id=current_user.id,
        token_denom=alert_in.token_denom,
        token_symbol=alert_in.token_symbol,
        target_price_usd=alert_in.target_price_usd,
        condition=alert_in.condition
    )
    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)
    return new_alert

@router.get("", response_model=List[PriceAlertResponse])
async def list_alerts(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    List all active and inactive price alerts for the user.
    """
    stmt = select(PriceAlert).where(PriceAlert.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: UUID, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a price alert.
    """
    stmt = delete(PriceAlert).where(PriceAlert.id == alert_id, PriceAlert.user_id == current_user.id)
    await db.execute(stmt)
    await db.commit()
    return {"message": "deleted"}

@router.get("/watchlist", response_model=List[WatchlistItemResponse])
async def list_watchlist(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get user's token watchlist.
    """
    stmt = select(WatchlistItem).where(WatchlistItem.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/watchlist", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    item_in: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a token to the user's watchlist.
    """
    new_item = WatchlistItem(
        user_id=current_user.id,
        token_denom=item_in.token_denom,
        token_symbol=item_in.token_symbol
    )
    db.add(new_item)
    try:
        await db.commit()
        await db.refresh(new_item)
    except Exception:
        # Likely unique constraint violation
        await db.rollback()
        raise HTTPException(status_code=400, detail="Already in watchlist")
    return new_item
