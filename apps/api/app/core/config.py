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
    APP_NAME: str = "StudyABHI"
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
    LLM_PROVIDER: str = "nvidia"  # ollama, nvidia, huggingface, openai
    LLM_MODEL: str = "mistralai/mistral-medium-3.5-128b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Primary API key (fallback for all models)
    NVIDIA_API_KEY: Optional[str] = None

    # Per-model dedicated API keys (each has its own rate limit)
    NVIDIA_CHAT_API_KEY: Optional[str] = None   # Mistral 128B — RAG/Chat
    NVIDIA_QUIZ_API_KEY: Optional[str] = None   # Llama 8B — Quiz generation
    NVIDIA_PLAN_API_KEY: Optional[str] = None   # Kimi k2.6 — Planning/Roadmap

    # Model routing — each task uses the optimal model
    NVIDIA_MODEL: str = "mistralai/mistral-medium-3.5-128b"       # fallback / default
    NVIDIA_CHAT_MODEL: str = "mistralai/mistral-medium-3.5-128b"  # RAG chat: best instruction following
    NVIDIA_QUIZ_MODEL: str = "meta/llama-3.1-8b-instruct"         # Quiz gen: fast + structured JSON
    NVIDIA_PLAN_MODEL: str = "moonshotai/kimi-k2.6"               # Roadmap planning: long-horizon reasoning

    NVIDIA_EMBED_MODEL: str = "nvidia/nv-embedqa-e5-v5"  # Embedding model
    NVIDIA_EMBED_DIM: int = 1024  # Embedding dimension

    def get_chat_api_key(self) -> Optional[str]:
        """Return dedicated chat key, fall back to primary."""
        return self.NVIDIA_CHAT_API_KEY or self.NVIDIA_API_KEY

    def get_quiz_api_key(self) -> Optional[str]:
        """Return dedicated quiz key, fall back to primary."""
        return self.NVIDIA_QUIZ_API_KEY or self.NVIDIA_API_KEY

    def get_plan_api_key(self) -> Optional[str]:
        """Return dedicated plan key, fall back to primary."""
        return self.NVIDIA_PLAN_API_KEY or self.NVIDIA_API_KEY


    # Vector Storage
    VECTOR_STORAGE_PATH: str = "data/vectors"

    # Legacy (unused but kept for config compatibility)
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
