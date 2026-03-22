from pydantic import BaseModel, ConfigDict, field_serializer
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.schemas.token import TokenBalance

class HoldingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    token_denom: str
    token_symbol: str
    amount: Decimal
    avg_price_usd: Decimal
    current_price_usd: Decimal
    total_value_usd: Decimal
    pnl_usd: Decimal
    pnl_percent: float

    @field_serializer('amount', 'avg_price_usd', 'current_price_usd', 'total_value_usd', 'pnl_usd')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

class PortfolioOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    total_portfolio_value_usd: Decimal
    account_balance_usd: Decimal
    holdings: List[HoldingSchema]
    on_chain_balances: List[TokenBalance]
    local_currency: str

    @field_serializer('total_portfolio_value_usd', 'account_balance_usd')
    def serialize_decimal(self, v: Decimal, _info):
        return str(v)

class PortfolioTransaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    onramp_amount: float
    onramp_currency: str
    onramp_status: str
    target_symbol: str
    target_amount: Optional[float] = None
    timestamp: datetime
