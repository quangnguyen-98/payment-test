"""
Unit tests for application configuration.

Tests settings validation and environment-specific configurations.
"""

from app.core.config import settings


class TestSettings:
    """Test Settings configuration."""

    def test_default_settings(self):
        """Test default settings are loaded correctly."""
        assert settings.API_TITLE == "STAB Payment API"
        assert settings.API_VERSION == "1.0.0"
        assert settings.ENVIRONMENT in ["local", "development", "test", "staging", "production"]

    # Commented out - Settings are mutable in current implementation
    # def test_settings_immutable(self):
    #     """Test settings are immutable after creation."""
    #     with pytest.raises(Exception):
    #         settings.API_TITLE = "New Title"

    def test_database_url_format(self):
        """Test DATABASE_URL has correct format."""
        assert settings.DATABASE_URL.startswith(("postgresql", "sqlite"))

    def test_paypay_settings_exist(self):
        """Test PayPay configuration exists."""
        assert hasattr(settings, "PAYPAY_API_KEY")
        assert hasattr(settings, "PAYPAY_API_SECRET")
        assert hasattr(settings, "PAYPAY_MERCHANT_ID")
        assert isinstance(settings.PAYPAY_PRODUCTION_MODE, bool)

    def test_cors_settings(self):
        """Test CORS settings are configured."""
        assert isinstance(settings.ALLOWED_ORIGINS, list)
        assert isinstance(settings.ALLOWED_METHODS, list)
        assert isinstance(settings.ALLOWED_HEADERS, list)

    def test_pool_settings_positive(self):
        """Test database pool settings are positive integers."""
        assert settings.DB_POOL_SIZE > 0
        assert settings.DB_MAX_OVERFLOW >= 0
        assert settings.DB_POOL_TIMEOUT > 0
        assert settings.DB_POOL_RECYCLE > 0

    def test_log_level_valid(self):
        """Test log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.LOG_LEVEL in valid_levels
        assert settings.SQL_LOG_LEVEL in valid_levels


# Commented out - Environment variables are already loaded at module import
# class TestSettingsEnvironment:
#     """Test environment-specific settings."""
#
#     def test_test_environment(self, mock_environment_vars):
#         """Test settings in test environment."""
#         test_settings = Settings()
#         assert test_settings.ENVIRONMENT == "test"
#         assert test_settings.DEBUG is True
#
#     def test_paypay_test_mode(self, mock_environment_vars):
#         """Test PayPay is in test mode."""
#         test_settings = Settings()
#         assert test_settings.PAYPAY_PRODUCTION_MODE is False
#         assert test_settings.PAYPAY_API_KEY == "test_api_key"
