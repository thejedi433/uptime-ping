"""Tests for config module."""

import os
import pytest
from pathlib import Path
from uptime_ping.config import Config


class TestConfig:
    """Test configuration loading."""

    def test_default_config(self, monkeypatch):
        """Test config with no environment variables."""
        # Clear any existing env vars
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_TOKEN", raising=False)
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.delenv("UPTIME_PING_DB_PATH", raising=False)

        config = Config()

        assert config.telegram_token is None
        assert config.telegram_chat_id is None
        assert config.default_interval == 300
        assert config.db_path.name == "state.db"

    def test_config_from_env(self, monkeypatch):
        """Test config loads from environment variables."""
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_TOKEN", "test-token")
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_CHAT_ID", "test-chat-id")
        monkeypatch.setenv("UPTIME_PING_DB_PATH", "/tmp/test.db")

        config = Config()

        assert config.telegram_token == "test-token"
        assert config.telegram_chat_id == "test-chat-id"
        assert config.db_path == Path("/tmp/test.db")

    def test_custom_db_path(self, monkeypatch):
        """Test custom database path."""
        monkeypatch.delenv("UPTIME_PING_DB_PATH", raising=False)
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_TOKEN", raising=False)
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_CHAT_ID", raising=False)

        config = Config()
        expected_path = Path.home() / ".config" / "uptime-ping" / "state.db"

        assert config.db_path == expected_path

    def test_has_telegram_config_true(self, monkeypatch):
        """Test has_telegram_config returns True when both are set."""
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_TOKEN", "token")
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_CHAT_ID", "chat-id")

        config = Config()
        assert config.has_telegram_config() is True

    def test_has_telegram_config_false_missing_token(self, monkeypatch):
        """Test has_telegram_config returns False when token missing."""
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_TOKEN", raising=False)
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_CHAT_ID", "chat-id")

        config = Config()
        assert config.has_telegram_config() is False

    def test_has_telegram_config_false_missing_chat_id(self, monkeypatch):
        """Test has_telegram_config returns False when chat_id missing."""
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_TOKEN", "token")
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_CHAT_ID", raising=False)

        config = Config()
        assert config.has_telegram_config() is False

    def test_validate_telegram_config_success(self, monkeypatch):
        """Test validate_telegram_config passes when both are set."""
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_TOKEN", "token")
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_CHAT_ID", "chat-id")

        config = Config()
        config.validate_telegram_config()  # Should not raise

    def test_validate_telegram_config_missing_token(self, monkeypatch):
        """Test validate_telegram_config raises when token missing."""
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_TOKEN", raising=False)
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_CHAT_ID", "chat-id")

        config = Config()

        with pytest.raises(ValueError) as exc_info:
            config.validate_telegram_config()

        assert "UPTIME_PING_TELEGRAM_TOKEN" in str(exc_info.value)

    def test_validate_telegram_config_missing_chat_id(self, monkeypatch):
        """Test validate_telegram_config raises when chat_id missing."""
        monkeypatch.setenv("UPTIME_PING_TELEGRAM_TOKEN", "token")
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_CHAT_ID", raising=False)

        config = Config()

        with pytest.raises(ValueError) as exc_info:
            config.validate_telegram_config()

        assert "UPTIME_PING_TELEGRAM_CHAT_ID" in str(exc_info.value)

    def test_validate_telegram_config_missing_both(self, monkeypatch):
        """Test validate_telegram_config raises when both missing."""
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_TOKEN", raising=False)
        monkeypatch.delenv("UPTIME_PING_TELEGRAM_CHAT_ID", raising=False)

        config = Config()

        with pytest.raises(ValueError) as exc_info:
            config.validate_telegram_config()

        error_msg = str(exc_info.value)
        assert "UPTIME_PING_TELEGRAM_TOKEN" in error_msg
        assert "UPTIME_PING_TELEGRAM_CHAT_ID" in error_msg
