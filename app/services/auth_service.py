import uuid
import secrets
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.config import settings
from app.core.database import get_db
from app.core.redis_client import redis_client
from app.models.user import User
from app.services.brevo_service import BrevoService

# Injective/EVM signature verification
from eth_account.messages import encode_defunct
from eth_account import Account

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
# class SimpleHasher:
#     def hash(self, p): return p + "_hash"
#     def verify(self, p, h): return h == p + "_hash"
# pwd_context = SimpleHasher()
brevo_service = BrevoService()

class AuthService:
    # ── Wallet Auth (Legacy) ──────────────────────────────────────────────────

    def generate_sign_message(self, wallet_address: str, nonce: str) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
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
        stored_nonce = await redis_client.get_cache(f"nonce:{wallet_address}")
        if not stored_nonce or stored_nonce != nonce:
            return False

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
        return True # Placeholder for Injective-py implementation

    # ── Email Auth logic ──────────────────────────────────────────────────────

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def get_password_hash(self, password: str) -> str:
        return self.hash_password(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def generate_otp(self) -> Tuple[str, datetime]:
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        return code, expires_at

    def generate_reset_token(self) -> Tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        return token, expires_at

    async def register_email_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
        country: str,
    ) -> User:
        # Check duplicate
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            logger.warning(f"Registration attempt for existing email: {email}")
            raise HTTPException(status_code=409, detail="Email already registered")

        logger.info(f"Registering new user: {email}")
        otp, expires = self.generate_otp()
        user = User(
            email=email,
            hashed_password=self.hash_password(password),
            full_name=full_name,
            country=country,
            auth_method="email",
            otp_code=otp,
            otp_expires_at=expires,
            email_verified=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Send OTP
        await brevo_service.send_otp_email(email, full_name, otp)
        logger.info(f"User registered: {email}, OTP sent")
        return user

    async def verify_otp(self, db: AsyncSession, email: str, otp_code: str) -> Tuple[str, User]:
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Email not found")

        if user.otp_code != otp_code:
            logger.warning(f"Invalid OTP attempt for: {email}")
            raise HTTPException(status_code=401, detail="Invalid verification code")
        
        if datetime.now(timezone.utc) > user.otp_expires_at:
            raise HTTPException(status_code=401, detail="Verification code expired")

        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        user.otp_code = None
        user.otp_expires_at = None
        await db.commit()

        # Send Welcome
        await brevo_service.send_welcome_email(user.email, user.full_name)
        
        token = self.create_access_token({"sub": str(user.id)})
        logger.info(f"Email verified: {email}")
        return token, user

    async def login_email(self, db: AsyncSession, email: str, password: str) -> Tuple[str, User]:
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        
        if not user or not self.verify_password(password, user.hashed_password):
            logger.warning(f"Failed login attempt for: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.email_verified:
            raise HTTPException(status_code=403, detail="Please verify your email first")

        user.last_active = datetime.now(timezone.utc)
        await db.commit()

        token = self.create_access_token({"sub": str(user.id)})
        logger.info(f"User logged in: {email}")
        return token, user

    async def resend_otp(self, db: AsyncSession, email: str) -> bool:
        # Rate limit check (Redis)
        count_key = f"otp_resend:{email}"
        count = await redis_client.get_cache(count_key)
        if count and int(count) >= settings.OTP_RESEND_LIMIT:
            raise HTTPException(status_code=429, detail="Too many resend attempts. Please try again later.")

        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Email not found")

        otp, expires = self.generate_otp()
        user.otp_code = otp
        user.otp_expires_at = expires
        await db.commit()

        # Update rate limit
        new_count = (int(count) + 1) if count else 1
        await redis_client.set_cache(count_key, str(new_count), ttl=3600)

        await brevo_service.send_otp_email(user.email, user.full_name, otp)
        return True

    async def request_password_reset(self, db: AsyncSession, email: str) -> bool:
        stmt = select(User).where(User.email == email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        
        if user:
            token, expires = self.generate_reset_token()
            user.password_reset_token = token
            user.password_reset_expires_at = expires
            await db.commit()
            await brevo_service.send_password_reset_email(user.email, user.full_name, token)
        
        return True # Always return true

    async def confirm_password_reset(self, db: AsyncSession, token: str, new_password: str) -> bool:
        stmt = select(User).where(User.password_reset_token == token)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        
        if not user or datetime.now(timezone.utc) > user.password_reset_expires_at:
            raise HTTPException(status_code=401, detail="Invalid or expired reset token")

        user.hashed_password = self.hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        await db.commit()
        return True

    # ── JWT & Dependency ──────────────────────────────────────────────────────

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
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
        if not token:
            raise credentials_exception

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            sub: str = payload.get("sub")
            if sub is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
            
        # Try finding by ID (new standard) or wallet_address (legacy)
        try:
            user_id = uuid.UUID(sub)
            stmt = select(User).where(User.id == user_id)
        except ValueError:
            stmt = select(User).where(User.wallet_address == sub)
            
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            raise credentials_exception
        return user

auth_service = AuthService()
