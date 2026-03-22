from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(...)
    
    # Redis
    REDIS_URL: str = Field(...)
    
    # Security
    SECRET_KEY: str = Field(...)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # Injective
    INJECTIVE_NETWORK: str = "mainnet"
    INJECTIVE_GRPC_ENDPOINT: str = Field(...)
    INJECTIVE_LCD_ENDPOINT: str = Field(...)
    
    # Onramp
    TRANSAK_API_KEY: str = Field(...)
    TRANSAK_SECRET_KEY: str = Field(...)
    TRANSAK_ENVIRONMENT: str = "STAGING"
    
    KADO_API_KEY: str = Field(...)
    
    # Push Notifications
    EXPO_PUSH_TOKEN_BASE: str = "https://exp.host/--/api/v2/push/send"
    
    # Brevo (Email)
    BREVO_API_KEY: str = Field("dummy")
    BREVO_SENDER_EMAIL: str = Field("noreply@fiatdex.app")
    BREVO_SENDER_NAME: str = Field("FiatDex")
    BREVO_OTP_TEMPLATE_ID: Optional[int] = Field(None)
    FRONTEND_BASE_URL: str = Field("https://app.fiatdex.app")
    
    # Paystack
    PAYSTACK_SECRET_KEY: str = Field("dummy")
    PAYSTACK_PUBLIC_KEY: str = Field("dummy")
    PAYSTACK_WEBHOOK_SECRET: Optional[str] = Field(None)
    
    # Business Rules
    MIN_PURCHASE_USD: float = 5.0
    MAX_PURCHASE_USD: float = 10000.0
    MAX_ACTIVE_ALERTS: int = 10
    OTP_RESEND_LIMIT: int = 3
    
    # General
    CORS_ORIGINS: List[str] = ["*"]
    ENVIRONMENT: str = "development"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
