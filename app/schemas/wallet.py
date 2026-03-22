from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from app.schemas.token import TokenBalance

class WalletAuthRequest(BaseModel):
    wallet_address: str
    wallet_type: str # "keplr", "metamask", "walletconnect"

class WalletNonceResponse(BaseModel):
    nonce: str
    message: str
    expires_in: int = 300

class WalletVerifyRequest(BaseModel):
    wallet_address: str
    wallet_type: str
    signature: str
    nonce: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class WalletBalance(BaseModel):
    total_value_usd: Decimal
    total_value_local: Decimal
    local_currency: str
    tokens: list[TokenBalance]

class UserResponse(BaseModel):
    wallet_address: str
    wallet_type: str
    preferred_currency: str
    is_active: bool
