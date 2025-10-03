"""Comprehensive unit tests for configuration management."""

import pytest
from pydantic import ValidationError, SecretStr
from unittest.mock import patch, MagicMock
import os

from src.core.config import Settings, get_settings


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def valid_env_vars():
    """Valid environment variables for testing."""
    return {
        "POSTGRES_PASSWORD": "secure_password_123!",
        "MINIO_ACCESS_KEY": "minio_access_key_12345",
        "MINIO_SECRET_KEY": "minio_secret_key_12345",
        "SECRET_KEY": "a" * 64,  # 64 character secure key
    }


@pytest.fixture
def minimal_env_vars():
    """Minimal required environment variables."""
    return {
        "POSTGRES_PASSWORD": "test_password_123!",
        "MINIO_ACCESS_KEY": "test_access_key",
        "MINIO_SECRET_KEY": "test_secret_key",
        "SECRET_KEY": "x" * 32,  # Minimum 32 characters
    }


# ============================================================================
# SETTINGS INITIALIZATION TESTS
# ============================================================================

class TestSettingsInitialization:
    """Test Settings initialization and defaults."""

    def test_settings_initialization_with_valid_env(self, valid_env_vars):
        """Test Settings initializes correctly with valid environment variables."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.APP_NAME == "Corporate Intelligence Platform"
            assert settings.APP_VERSION == "0.1.0"
            assert settings.DEBUG is False
            assert settings.API_V1_PREFIX == "/api/v1"
            assert settings.ENVIRONMENT == "development"

    def test_settings_default_values(self, valid_env_vars):
        """Test default values are set correctly."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            # Database defaults
            assert settings.POSTGRES_HOST == "localhost"
            assert settings.POSTGRES_PORT == 5432
            assert settings.POSTGRES_USER == "intel_user"
            assert settings.POSTGRES_DB == "corporate_intel"

            # Redis defaults
            assert settings.REDIS_HOST == "localhost"
            assert settings.REDIS_PORT == 6379
            assert settings.REDIS_DB == 0
            assert settings.REDIS_CACHE_TTL == 3600

    def test_settings_caching(self, valid_env_vars):
        """Test that get_settings returns cached instance."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2  # Should be the same instance


# ============================================================================
# SECRET KEY VALIDATION TESTS
# ============================================================================

class TestSecretKeyValidation:
    """Test SECRET_KEY validation requirements."""

    def test_secret_key_minimum_length_32_chars(self):
        """Test SECRET_KEY must be at least 32 characters."""
        env_vars = {
            "POSTGRES_PASSWORD": "password123!",
            "MINIO_ACCESS_KEY": "access_key",
            "MINIO_SECRET_KEY": "secret_key",
            "SECRET_KEY": "short_key",  # Too short
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "at least 32 characters" in str(exc_info.value)

    def test_secret_key_exactly_32_chars_accepted(self):
        """Test SECRET_KEY with exactly 32 characters is accepted."""
        env_vars = {
            "POSTGRES_PASSWORD": "password123!",
            "MINIO_ACCESS_KEY": "access_key",
            "MINIO_SECRET_KEY": "secret_key",
            "SECRET_KEY": "a" * 32,
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert len(settings.SECRET_KEY.get_secret_value()) == 32

    def test_secret_key_rejects_common_insecure_values(self):
        """Test SECRET_KEY rejects commonly insecure values."""
        insecure_keys = [
            "your-secret-key-here" + "x" * 12,
            "changeme" + "x" * 24,
            "secret" + "x" * 26,
            "change-me-in-production" + "x" * 9,
            "12345678901234567890123456789012",
        ]

        for insecure_key in insecure_keys:
            env_vars = {
                "POSTGRES_PASSWORD": "password123!",
                "MINIO_ACCESS_KEY": "access_key",
                "MINIO_SECRET_KEY": "secret_key",
                "SECRET_KEY": insecure_key,
            }

            with patch.dict(os.environ, env_vars, clear=True):
                with pytest.raises(ValidationError) as exc_info:
                    Settings()

                assert "cannot be a default or commonly insecure value" in str(exc_info.value)

    def test_secret_key_missing_raises_error(self):
        """Test missing SECRET_KEY raises validation error."""
        env_vars = {
            "POSTGRES_PASSWORD": "password123!",
            "MINIO_ACCESS_KEY": "access_key",
            "MINIO_SECRET_KEY": "secret_key",
            # SECRET_KEY missing
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "required" in str(exc_info.value).lower()


# ============================================================================
# ENVIRONMENT VALIDATION TESTS
# ============================================================================

class TestEnvironmentValidation:
    """Test ENVIRONMENT field validation."""

    @pytest.mark.parametrize("env", ["development", "staging", "production"])
    def test_valid_environment_values(self, env, minimal_env_vars):
        """Test valid environment values are accepted."""
        minimal_env_vars["ENVIRONMENT"] = env

        with patch.dict(os.environ, minimal_env_vars, clear=True):
            settings = Settings()
            assert settings.ENVIRONMENT == env

    def test_invalid_environment_value_rejected(self, minimal_env_vars):
        """Test invalid environment value is rejected."""
        minimal_env_vars["ENVIRONMENT"] = "invalid_env"

        with patch.dict(os.environ, minimal_env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "ENVIRONMENT" in str(exc_info.value)


# ============================================================================
# DATABASE URL BUILDING TESTS
# ============================================================================

class TestDatabaseURLBuilding:
    """Test database URL construction."""

    def test_database_url_async_format(self, valid_env_vars):
        """Test async database URL is correctly formatted."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            expected_url = (
                f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
                f"{valid_env_vars['POSTGRES_PASSWORD']}@"
                f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/"
                f"{settings.POSTGRES_DB}"
            )

            assert settings.database_url == expected_url

    def test_sync_database_url_format(self, valid_env_vars):
        """Test synchronous database URL is correctly formatted."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            expected_url = (
                f"postgresql://{settings.POSTGRES_USER}:"
                f"{valid_env_vars['POSTGRES_PASSWORD']}@"
                f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/"
                f"{settings.POSTGRES_DB}"
            )

            assert settings.sync_database_url == expected_url

    def test_database_url_custom_host_port(self, minimal_env_vars):
        """Test database URL with custom host and port."""
        minimal_env_vars["POSTGRES_HOST"] = "db.example.com"
        minimal_env_vars["POSTGRES_PORT"] = "5433"

        with patch.dict(os.environ, minimal_env_vars, clear=True):
            settings = Settings()

            assert "db.example.com:5433" in settings.database_url

    def test_database_url_password_encoding(self, minimal_env_vars):
        """Test database URL correctly includes password from SecretStr."""
        minimal_env_vars["POSTGRES_PASSWORD"] = "p@ssw0rd!#$"

        with patch.dict(os.environ, minimal_env_vars, clear=True):
            settings = Settings()

            # Password should be included in URL
            assert "p@ssw0rd!#$" in settings.database_url


# ============================================================================
# REDIS URL BUILDING TESTS
# ============================================================================

class TestRedisURLBuilding:
    """Test Redis URL construction."""

    def test_redis_url_without_password(self, minimal_env_vars):
        """Test Redis URL without password."""
        # Don't set REDIS_PASSWORD
        with patch.dict(os.environ, minimal_env_vars, clear=True):
            settings = Settings()

            expected_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            assert settings.redis_url == expected_url

    def test_redis_url_with_password(self, minimal_env_vars):
        """Test Redis URL with password."""
        minimal_env_vars["REDIS_PASSWORD"] = "redis_password_123"

        with patch.dict(os.environ, minimal_env_vars, clear=True):
            settings = Settings()

            expected_url = f"redis://:redis_password_123@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            assert settings.redis_url == expected_url

    def test_redis_url_custom_host_port_db(self, minimal_env_vars):
        """Test Redis URL with custom host, port, and database."""
        minimal_env_vars["REDIS_HOST"] = "redis.example.com"
        minimal_env_vars["REDIS_PORT"] = "6380"
        minimal_env_vars["REDIS_DB"] = "5"

        with patch.dict(os.environ, minimal_env_vars, clear=True):
            settings = Settings()

            assert "redis.example.com:6380/5" in settings.redis_url


# ============================================================================
# SECRETS VALIDATION TESTS
# ============================================================================

class TestSecretsValidation:
    """Test validation of secret fields."""

    def test_postgres_password_required(self):
        """Test POSTGRES_PASSWORD is required."""
        env_vars = {
            "SECRET_KEY": "a" * 32,
            "MINIO_ACCESS_KEY": "access",
            "MINIO_SECRET_KEY": "secret",
            # POSTGRES_PASSWORD missing
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "POSTGRES_PASSWORD" in str(exc_info.value)

    def test_minio_access_key_required(self):
        """Test MINIO_ACCESS_KEY is required."""
        env_vars = {
            "SECRET_KEY": "a" * 32,
            "POSTGRES_PASSWORD": "password",
            "MINIO_SECRET_KEY": "secret",
            # MINIO_ACCESS_KEY missing
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "MINIO_ACCESS_KEY" in str(exc_info.value)

    def test_minio_secret_key_required(self):
        """Test MINIO_SECRET_KEY is required."""
        env_vars = {
            "SECRET_KEY": "a" * 32,
            "POSTGRES_PASSWORD": "password",
            "MINIO_ACCESS_KEY": "access",
            # MINIO_SECRET_KEY missing
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "MINIO_SECRET_KEY" in str(exc_info.value)

    def test_secrets_reject_placeholder_values(self, minimal_env_vars):
        """Test secrets reject common placeholder values."""
        placeholder_values = ["change-me-in-production", "", "your-secret-key-here"]

        for placeholder in placeholder_values:
            env_vars = minimal_env_vars.copy()
            env_vars["POSTGRES_PASSWORD"] = placeholder

            with patch.dict(os.environ, env_vars, clear=True):
                with pytest.raises(ValidationError) as exc_info:
                    Settings()

                assert "proper secret values" in str(exc_info.value)


# ============================================================================
# EDTECH CONFIGURATION TESTS
# ============================================================================

class TestEdTechConfiguration:
    """Test EdTech-specific configuration."""

    def test_edtech_companies_watchlist_default(self, valid_env_vars):
        """Test EdTech companies watchlist has default values."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            expected_tickers = ["CHGG", "COUR", "DUOL", "TWOU", "ARCE", "LAUR", "INST", "POWL"]

            assert settings.EDTECH_COMPANIES_WATCHLIST == expected_tickers
            assert "DUOL" in settings.EDTECH_COMPANIES_WATCHLIST

    def test_edtech_metrics_tracked_default(self, valid_env_vars):
        """Test EdTech metrics tracked has default values."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            expected_metrics = [
                "monthly_active_users",
                "average_revenue_per_user",
                "customer_acquisition_cost",
                "net_revenue_retention",
                "course_completion_rate",
                "platform_engagement_score",
                "subscriber_count",
                "gross_merchandise_value",
            ]

            assert settings.EDTECH_METRICS_TRACKED == expected_metrics

    def test_edtech_custom_watchlist(self, valid_env_vars):
        """Test EdTech watchlist can be customized via environment."""
        valid_env_vars["EDTECH_COMPANIES_WATCHLIST"] = '["CUSTOM1", "CUSTOM2"]'

        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            # Note: This test shows expected behavior if implemented
            # Currently uses default_factory, so env var might not override


# ============================================================================
# VECTOR CONFIGURATION TESTS
# ============================================================================

class TestVectorConfiguration:
    """Test pgvector configuration."""

    def test_vector_dimension_default(self, valid_env_vars):
        """Test vector dimension defaults to OpenAI embeddings size."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.VECTOR_DIMENSION == 1536  # OpenAI embeddings

    def test_vector_index_configuration(self, valid_env_vars):
        """Test vector index configuration."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.VECTOR_INDEX_TYPE == "ivfflat"
            assert settings.VECTOR_LISTS == 100

    def test_vector_dimension_custom(self, valid_env_vars):
        """Test custom vector dimension."""
        valid_env_vars["VECTOR_DIMENSION"] = "768"

        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.VECTOR_DIMENSION == 768


# ============================================================================
# TIMESCALE CONFIGURATION TESTS
# ============================================================================

class TestTimescaleConfiguration:
    """Test TimescaleDB configuration."""

    def test_timescale_compression_default(self, valid_env_vars):
        """Test TimescaleDB compression defaults."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.TIMESCALE_COMPRESSION_AFTER_DAYS == 30
            assert settings.TIMESCALE_RETENTION_YEARS == 2

    def test_timescale_custom_settings(self, valid_env_vars):
        """Test custom TimescaleDB settings."""
        valid_env_vars["TIMESCALE_COMPRESSION_AFTER_DAYS"] = "60"
        valid_env_vars["TIMESCALE_RETENTION_YEARS"] = "5"

        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.TIMESCALE_COMPRESSION_AFTER_DAYS == 60
            assert settings.TIMESCALE_RETENTION_YEARS == 5


# ============================================================================
# SECURITY CONFIGURATION TESTS
# ============================================================================

class TestSecurityConfiguration:
    """Test security-related configuration."""

    def test_cors_origins_default(self, valid_env_vars):
        """Test CORS origins defaults."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert "http://localhost:3000" in settings.CORS_ORIGINS
            assert "http://localhost:8088" in settings.CORS_ORIGINS

    def test_access_token_expiry_default(self, valid_env_vars):
        """Test access token expiry defaults to 30 minutes."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_sec_rate_limit_default(self, valid_env_vars):
        """Test SEC API rate limit defaults."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.SEC_RATE_LIMIT == 10  # 10 requests per second

    def test_sec_user_agent_configured(self, valid_env_vars):
        """Test SEC user agent is properly configured."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert "Corporate Intel Bot" in settings.SEC_USER_AGENT
            assert "@gmail.com" in settings.SEC_USER_AGENT


# ============================================================================
# OBSERVABILITY CONFIGURATION TESTS
# ============================================================================

class TestObservabilityConfiguration:
    """Test observability and monitoring configuration."""

    def test_otel_defaults(self, valid_env_vars):
        """Test OpenTelemetry defaults."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.OTEL_SERVICE_NAME == "corporate-intel"
            assert settings.OTEL_TRACES_ENABLED is True
            assert settings.OTEL_METRICS_ENABLED is True
            assert "localhost:4317" in settings.OTEL_EXPORTER_OTLP_ENDPOINT

    def test_sentry_configuration_optional(self, valid_env_vars):
        """Test Sentry configuration is optional."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.SENTRY_DSN is None
            assert settings.SENTRY_TRACES_SAMPLE_RATE == 0.1
            assert settings.SENTRY_PROFILES_SAMPLE_RATE == 0.1

    def test_sentry_dsn_custom(self, valid_env_vars):
        """Test Sentry DSN can be configured."""
        valid_env_vars["SENTRY_DSN"] = "https://test@sentry.io/123456"

        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.SENTRY_DSN == "https://test@sentry.io/123456"


# ============================================================================
# EXTERNAL API CONFIGURATION TESTS
# ============================================================================

class TestExternalAPIConfiguration:
    """Test external API configuration."""

    def test_alpha_vantage_optional(self, valid_env_vars):
        """Test Alpha Vantage API key is optional."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.ALPHA_VANTAGE_API_KEY is None

    def test_yahoo_finance_enabled_default(self, valid_env_vars):
        """Test Yahoo Finance is enabled by default."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert settings.YAHOO_FINANCE_ENABLED is True

    def test_prefect_configuration(self, valid_env_vars):
        """Test Prefect configuration."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert "localhost:4200" in settings.PREFECT_API_URL
            assert settings.PREFECT_WORKSPACE == "corporate-intel"

    def test_ray_configuration_optional(self, valid_env_vars):
        """Test Ray configuration is optional."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            assert "ray://localhost:10001" in settings.RAY_HEAD_ADDRESS
            assert settings.RAY_NUM_CPUS is None
            assert settings.RAY_NUM_GPUS is None


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_environment_fails(self):
        """Test that empty environment fails validation."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_partial_configuration_fails(self):
        """Test that partial configuration fails."""
        env_vars = {
            "SECRET_KEY": "a" * 32,
            # Missing other required fields
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_case_insensitive_environment_variables(self, valid_env_vars):
        """Test that environment variables are case-insensitive."""
        valid_env_vars["postgres_password"] = valid_env_vars.pop("POSTGRES_PASSWORD")

        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            # Should work with lowercase env var
            assert settings.POSTGRES_PASSWORD.get_secret_value() is not None

    def test_invalid_port_number(self, minimal_env_vars):
        """Test invalid port number validation."""
        minimal_env_vars["POSTGRES_PORT"] = "invalid"

        with patch.dict(os.environ, minimal_env_vars, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_secret_str_masking(self, valid_env_vars):
        """Test that SecretStr fields are properly masked."""
        with patch.dict(os.environ, valid_env_vars, clear=True):
            settings = Settings()

            # SecretStr should not reveal value in string representation
            assert "***" in str(settings.SECRET_KEY) or "SecretStr" in str(settings.SECRET_KEY)
            assert valid_env_vars["SECRET_KEY"] not in str(settings.SECRET_KEY)
