"""Tests for configuration module."""

from app.config import Settings, get_settings


class TestSettings:
    """Test Settings class."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.ws_ping_interval == 30
        assert settings.ws_ping_timeout == 60

    def test_is_development(self):
        """Test is_development computed property."""
        settings = Settings(environment="development")
        assert settings.is_development is True

        settings = Settings(environment="production")
        assert settings.is_development is False

    def test_debug_namespaces_parsing(self):
        """Test debug_namespaces computed property."""
        settings = Settings(log_debug_namespaces="")
        assert settings.debug_namespaces == []

        settings = Settings(log_debug_namespaces="ws,auth,db")
        assert settings.debug_namespaces == ["ws", "auth", "db"]

        settings = Settings(log_debug_namespaces=" ws , auth , db ")
        assert settings.debug_namespaces == ["ws", "auth", "db"]

    def test_redact_url(self):
        """Test URL redaction for logging."""
        url = "postgresql+asyncpg://user:secret@localhost:5432/db"
        redacted = Settings._redact_url(url)
        assert "secret" not in redacted
        assert "***" in redacted

        # URL without password
        url = "redis://localhost:6379/0"
        redacted = Settings._redact_url(url)
        assert redacted == url


class TestGetSettings:
    """Test get_settings function."""

    def test_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        # Clear cache
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_cached(self):
        """Test that settings are cached."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
