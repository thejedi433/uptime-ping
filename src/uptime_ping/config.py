"""Configuration management for uptime-ping."""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration loader from environment variables."""

    def __init__(self):
        self.telegram_token: Optional[str] = os.getenv("UPTIME_PING_TELEGRAM_TOKEN")
        self.telegram_chat_id: Optional[str] = os.getenv("UPTIME_PING_TELEGRAM_CHAT_ID")
        self.db_path: Path = self._get_db_path()
        self.default_interval: int = 300  # 5 minutes

    def _get_db_path(self) -> Path:
        """Get database path, defaulting to user config directory."""
        custom_path = os.getenv("UPTIME_PING_DB_PATH")
        if custom_path:
            return Path(custom_path)

        # Default to ~/.config/uptime-ping/state.db
        config_dir = Path.home() / ".config" / "uptime-ping"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "state.db"

    def has_telegram_config(self) -> bool:
        """Check if Telegram credentials are configured."""
        return bool(self.telegram_token and self.telegram_chat_id)

    def validate_telegram_config(self) -> None:
        """Raise ValueError if Telegram config is missing."""
        if not self.has_telegram_config():
            missing = []
            if not self.telegram_token:
                missing.append("UPTIME_PING_TELEGRAM_TOKEN")
            if not self.telegram_chat_id:
                missing.append("UPTIME_PING_TELEGRAM_CHAT_ID")
            raise ValueError(
                f"Missing Telegram configuration: {', '.join(missing)}. "
                "Set these environment variables to enable notifications."
            )
