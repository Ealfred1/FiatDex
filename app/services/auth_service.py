import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.redis_client import redis_client
from app.models.user import User

# Injective/EVM signature verification
from eth_account.messages import encode_defunct
from eth_account import Account

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/wallet/auth/verify")

class AuthService:
    def generate_sign_message(self, wallet_address: str, nonce: str) -> str:
        """
        Generate the message the user must sign to authenticate.
        """
        timestamp = datetime.utcnow().isoformat()
        return (
            f"FiatDex Authentication\n"
            f"Address: {wallet_address}\n"
            f"Nonce: {nonce}\n"
            f"Timestamp: {timestamp}"
        )

    async def verify_signature(
        self,
        wallet_address: str,
        wallet_type: str,
        signature: str,
        message: str,
        nonce: str
    ) -> bool:
        """
        Verify wallet signature based on wallet type.
        """
        # 1. Verify nonce exists in Redis
        stored_nonce = await redis_client.get_cache(f"nonce:{wallet_address}")
        if not stored_nonce or stored_nonce != nonce:
            return False

        # 2. Verify signature
        if wallet_type == "metamask":
            return self.verify_metamask_signature(wallet_address, signature, message)
        elif wallet_type == "keplr":
            return self.verify_keplr_signature(wallet_address, signature, message)
        
        return False

    def verify_metamask_signature(self, wallet_address: str, signature: str, message: str) -> bool:
        try:
            message_hash = encode_defunct(text=message)
            recovered_address = Account.recover_message(message_hash, signature=signature)
            return recovered_address.lower() == wallet_address.lower()
        except Exception:
            return False

    def verify_keplr_signature(self, wallet_address: str, signature: str, message: str) -> bool:
        # Simplified for Injective (using bech32/cosmos signature logic)
        # In actual implementation, we might use injective-py's internal classes
        # for verifying Cosmos-style signatures.
        # For now, placeholder verification.
        return True # Placeholder

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def get_current_user(
        self, 
        token: str = Depends(oauth2_scheme), 
        db: AsyncSession = Depends(get_db)
    ) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            wallet_address: str = payload.get("sub")
            if wallet_address is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
            
        stmt = select(User).where(User.wallet_address == wallet_address)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            raise credentials_exception
        return user

auth_service = AuthService()
