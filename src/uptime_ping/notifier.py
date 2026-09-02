"""Telegram notifier for uptime alerts."""

from typing import Optional
import requests

from .storage import CheckResult


class Notifier:
    """Send Telegram notifications about uptime status."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def notify_down(self, result: CheckResult) -> bool:
        """Send alert that a URL is down."""
        message = self._format_down_message(result)
        return self._send(message)

    def notify_up(self, result: CheckResult) -> bool:
        """Send alert that a URL has recovered."""
        message = self._format_up_message(result)
        return self._send(message)

    def _format_down_message(self, result: CheckResult) -> str:
        """Format a down alert message."""
        lines = [f"🔴 DOWN: {result.url}"]
        if result.status_code is not None:
            lines.append(f"Status: {result.status_code}")
        if result.error:
            lines.append(f"Error: {result.error}")
        if result.latency_ms is not None:
            lines.append(f"Latency: {result.latency_ms:.0f}ms")
        lines.append(f"Time: {result.checked_at}")
        return "\n".join(lines)

    def _format_up_message(self, result: CheckResult) -> str:
        """Format a recovery message."""
        lines = [f"🟢 UP: {result.url}"]
        if result.status_code is not None:
            lines.append(f"Status: {result.status_code}")
        if result.latency_ms is not None:
            lines.append(f"Latency: {result.latency_ms:.0f}ms")
        lines.append(f"Time: {result.checked_at}")
        return "\n".join(lines)

    def _send(self, text: str) -> bool:
        """Send a message via Telegram API. Returns True on success."""
        url = self.API_URL.format(token=self.token)
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("ok", False)
        except requests.exceptions.RequestException:
            return False
