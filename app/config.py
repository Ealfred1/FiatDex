from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # Injective
    INJECTIVE_NETWORK: str = "mainnet"
    INJECTIVE_GRPC_ENDPOINT: str = Field(..., env="INJECTIVE_GRPC_ENDPOINT")
    INJECTIVE_LCD_ENDPOINT: str = Field(..., env="INJECTIVE_LCD_ENDPOINT")
    
    # Onramp
    TRANSAK_API_KEY: str = Field(..., env="TRANSAK_API_KEY")
    TRANSAK_SECRET_KEY: str = Field(..., env="TRANSAK_SECRET_KEY")
    TRANSAK_ENVIRONMENT: str = "STAGING"
    
    KADO_API_KEY: str = Field(..., env="KADO_API_KEY")
    
    # Push Notifications
    EXPO_PUSH_TOKEN_BASE: str = "https://exp.host/--/api/v2/push/send"
    
    # Brevo (Email)
    BREVO_API_KEY: str = Field("dummy", env="BREVO_API_KEY")
    BREVO_SENDER_EMAIL: str = Field("noreply@fiatdex.app", env="BREVO_SENDER_EMAIL")
    BREVO_SENDER_NAME: str = Field("FiatDex", env="BREVO_SENDER_NAME")
    BREVO_OTP_TEMPLATE_ID: Optional[int] = Field(None, env="BREVO_OTP_TEMPLATE_ID")
    FRONTEND_BASE_URL: str = Field("https://app.fiatdex.app", env="FRONTEND_BASE_URL")
    
    # Paystack
    PAYSTACK_SECRET_KEY: str = Field("dummy", env="PAYSTACK_SECRET_KEY")
    PAYSTACK_PUBLIC_KEY: str = Field("dummy", env="PAYSTACK_PUBLIC_KEY")
    PAYSTACK_WEBHOOK_SECRET: Optional[str] = Field(None, env="PAYSTACK_WEBHOOK_SECRET")
    
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
