"""Application configuration."""

from typing import Optional, List
from pydantic import BaseSettings, Field, PostgresDsn, RedisDsn
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Corporate Intelligence Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Security
    SECRET_KEY: str = Field(default="", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8050"],
        env="BACKEND_CORS_ORIGINS"
    )
    
    # Database
    POSTGRES_HOST: str = Field(default="localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field(default="intel_user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="corporate_intel", env="POSTGRES_DB")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # MinIO
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="", env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="", env="MINIO_SECRET_KEY")
    MINIO_USE_SSL: bool = Field(default=False, env="MINIO_USE_SSL")
    MINIO_BUCKET_DOCUMENTS: str = Field(default="corporate-documents", env="MINIO_BUCKET_DOCUMENTS")
    MINIO_BUCKET_REPORTS: str = Field(default="analysis-reports", env="MINIO_BUCKET_REPORTS")
    
    # Prefect
    PREFECT_API_URL: str = Field(default="http://localhost:4200/api", env="PREFECT_API_URL")
    
    # Ray
    RAY_HEAD_ADDRESS: str = Field(default="ray://localhost:10001", env="RAY_HEAD_ADDRESS")
    
    # External APIs
    ALPHA_VANTAGE_API_KEY: str = Field(default="", env="ALPHA_VANTAGE_API_KEY")
    NEWSAPI_KEY: str = Field(default="", env="NEWSAPI_KEY")
    CRUNCHBASE_API_KEY: str = Field(default="", env="CRUNCHBASE_API_KEY")
    GITHUB_TOKEN: str = Field(default="", env="GITHUB_TOKEN")
    
    # SEC EDGAR
    SEC_USER_AGENT: str = Field(
        default="Corporate Intel Platform/1.0 (admin@example.com)",
        env="SEC_USER_AGENT"
    )
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default="http://localhost:4317",
        env="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    OTEL_SERVICE_NAME: str = Field(
        default="corporate-intel-api",
        env="OTEL_SERVICE_NAME"
    )
    OTEL_ENABLED: bool = Field(default=True, env="OTEL_ENABLED")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Data Quality
    DATA_QUALITY_ENABLED: bool = Field(default=True, env="DATA_QUALITY_ENABLED")
    ANOMALY_DETECTION_ENABLED: bool = Field(default=True, env="ANOMALY_DETECTION_ENABLED")
    
    # Embeddings
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    EMBEDDING_DIMENSION: int = Field(default=384, env="EMBEDDING_DIMENSION")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    
    # Cache
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    CACHE_ENABLED: bool = Field(default=True, env="CACHE_ENABLED")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Generate secret key if not set
if not settings.SECRET_KEY:
    import secrets
    settings.SECRET_KEY = secrets.token_urlsafe(32)