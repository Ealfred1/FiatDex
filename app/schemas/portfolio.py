from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.schemas.token import TokenBalance

class PortfolioOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    total_value_usd: float
    total_value_local: float
    local_currency: str
    change_24h: float
    holdings: List[TokenBalance]

class PortfolioTransaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    onramp_amount: float
    onramp_currency: str
    onramp_status: str
    target_symbol: str
    target_amount: Optional[float] = None
    timestamp: datetime
