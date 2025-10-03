"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and type safety."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    APP_NAME: str = "Corporate Intelligence Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "intel_user"
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str = "corporate_intel"
    
    # TimescaleDB specific
    TIMESCALE_COMPRESSION_AFTER_DAYS: int = 30
    TIMESCALE_RETENTION_YEARS: int = 2
    
    # pgvector
    VECTOR_DIMENSION: int = 1536  # OpenAI embeddings dimension
    VECTOR_INDEX_TYPE: str = "ivfflat"
    VECTOR_LISTS: int = 100
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[SecretStr] = None
    REDIS_DB: int = 0
    REDIS_CACHE_TTL: int = 3600  # 1 hour default
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: SecretStr
    MINIO_SECRET_KEY: SecretStr
    MINIO_SECURE: bool = False
    MINIO_BUCKET_DOCUMENTS: str = "corporate-documents"
    MINIO_BUCKET_REPORTS: str = "analysis-reports"
    
    # Prefect
    PREFECT_API_URL: str = "http://localhost:4200/api"
    PREFECT_WORKSPACE: str = "corporate-intel"
    
    # Ray
    RAY_HEAD_ADDRESS: str = "ray://localhost:10001"
    RAY_NUM_CPUS: Optional[int] = None
    RAY_NUM_GPUS: Optional[int] = None
    
    # SEC EDGAR API
    SEC_USER_AGENT: str = Field(
        default="Corporate Intel Bot/1.0 (brandon.lambert87@gmail.com)"
    )
    SEC_RATE_LIMIT: int = 10  # requests per second
    
    # Financial APIs
    ALPHA_VANTAGE_API_KEY: Optional[SecretStr] = None
    YAHOO_FINANCE_ENABLED: bool = True
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "corporate-intel"
    OTEL_TRACES_ENABLED: bool = True
    OTEL_METRICS_ENABLED: bool = True
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1
    
    # Security
    SECRET_KEY: SecretStr = Field(
        description="Secret key for JWT and sessions - MUST be set via environment variable"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8088"]
    
    # EdTech Specific
    EDTECH_COMPANIES_WATCHLIST: list[str] = Field(
        default_factory=lambda: [
            "CHGG",  # Chegg
            "COUR",  # Coursera
            "DUOL",  # Duolingo
            "TWOU",  # 2U
            "ARCE",  # Arco Platform
            "LAUR",  # Laureate Education
            "INST",  # Instructure
            "POWL",  # Powell Industries (Powerschool)
        ]
    )
    
    EDTECH_METRICS_TRACKED: list[str] = Field(
        default_factory=lambda: [
            "monthly_active_users",
            "average_revenue_per_user",
            "customer_acquisition_cost",
            "net_revenue_retention",
            "course_completion_rate",
            "platform_engagement_score",
            "subscriber_count",
            "gross_merchandise_value",
        ]
    )
    
    @field_validator("POSTGRES_PASSWORD", "REDIS_PASSWORD", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "SECRET_KEY")
    @classmethod
    def validate_secrets(cls, v: Optional[SecretStr]) -> SecretStr:
        """Ensure secrets are not default values in production."""
        if not v:
            raise ValueError("Required secret value is not set - check your .env file")
        secret_value = v.get_secret_value()
        if secret_value in ["change-me-in-production", "", "your-secret-key-here"]:
            raise ValueError("Please set proper secret values for production")
        return v
    
    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL."""
        password = self.POSTGRES_PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def sync_database_url(self) -> str:
        """Build synchronous PostgreSQL connection URL."""
        password = self.POSTGRES_PASSWORD.get_secret_value()
        return f"postgresql://{self.POSTGRES_USER}:{password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def redis_url(self) -> str:
        """Build Redis connection URL."""
        if self.REDIS_PASSWORD:
            password = self.REDIS_PASSWORD.get_secret_value()
            return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()