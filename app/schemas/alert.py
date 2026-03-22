from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional, Union
from uuid import UUID

class AlertCreate(BaseModel):
    token_denom: str
    token_symbol: str
    target_price_usd: float
    condition: str # "above", "below"

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    token_denom: str
    token_symbol: str
    target_price_usd: float
    condition: str
    is_active: bool
    created_at: datetime

class WatchlistAddItem(BaseModel):
    token_denom: str
    token_symbol: str

class WatchlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    token_denom: str
    token_symbol: str
    added_at: datetime
