from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional, Dict
from datetime import datetime

class FiatQuote(BaseModel):
    provider: str
    fiat_amount: Decimal
    fiat_currency: str
    crypto_amount: Decimal
    crypto_currency: str = "INJ"
    total_fee: Decimal
    network_fee: Decimal
    service_fee: Decimal
    conversion_price: Decimal
    expires_at: datetime

class OnrampQuote(BaseModel):
    provider: str
    fiat_amount: Decimal
    fiat_currency: str
    estimated_inj_amount: Decimal
    estimated_target_token_amount: Decimal
    exchange_rate: Decimal
    fees: Dict[str, Decimal]
    min_amount: Decimal
    max_amount: Decimal
    supported_payment_methods: List[str]

class OnrampSession(BaseModel):
    transaction_id: str
    widget_url: str
    provider: str
    order_id: str
    expires_at: datetime

class TransakOrderResult(BaseModel):
    order_id: str
    status: str
    fiat_amount: Decimal
    crypto_amount: Decimal
    wallet_address: str
    tx_hash: Optional[str] = None

class KadoOrderResult(BaseModel):
    order_id: str
    status: str
    fiat_amount: Decimal
    crypto_amount: Decimal
    wallet_address: str
    tx_hash: Optional[str] = None
