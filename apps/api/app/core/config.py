"""
Application Configuration
Environment-based settings management using Pydantic Settings
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All sensitive data should be stored in .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "UPSC AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://upsc_user:upsc_password@localhost:5432/upsc_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT Authentication
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Hashing
    BCRYPT_ROUNDS: int = 12
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # AI Services
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "phi3:mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: Optional[str] = None
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # Email (for future use)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()


# Export settings instance
settings = get_settings()
