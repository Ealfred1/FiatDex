from typing import List
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
    
    # General
    CORS_ORIGINS: List[str] = ["*"]
    ENVIRONMENT: str = "development"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
