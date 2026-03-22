from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import List

class RecentTrade(BaseModel):
    order_hash: str
    subaccount_id: str
    market_id: str
    trade_execution_type: str
    trade_direction: str
    price: Decimal
    quantity: Decimal
    fee: Decimal
    executed_at: datetime
    fee_recipient: str

class PriceLevel(BaseModel):
    price: Decimal
    quantity: Decimal

class Orderbook(BaseModel):
    bids: List[PriceLevel]
    asks: List[PriceLevel]
    sequence: int
    timestamp: datetime
