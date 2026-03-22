from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from app.schemas.token import TokenBalance

class PortfolioOverview(BaseModel):
    total_value_usd: float
    total_value_local: float
    local_currency: str
    change_24h: float
    holdings: List[TokenBalance]

class PortfolioTransaction(BaseModel):
    id: str
    onramp_amount: float
    onramp_currency: str
    onramp_status: str
    target_symbol: str
    target_amount: Optional[float] = None
    timestamp: datetime
