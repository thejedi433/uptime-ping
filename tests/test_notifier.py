"""Tests for notifier module."""

import pytest
from unittest.mock import patch, Mock
from uptime_ping.notifier import Notifier
from uptime_ping.storage import CheckResult


class TestNotifier:
    """Test Telegram notifications."""

    @pytest.fixture
    def notifier(self):
        """Create a notifier instance."""
        return Notifier(token="test-token", chat_id="test-chat-id")

    def test_notify_down_success(self, notifier):
        """Test sending down notification."""
        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=False,
            error="Connection timeout",
            latency_ms=150.5,
        )

        with patch("uptime_ping.notifier.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_post.return_value = mock_response

            success = notifier.notify_down(result)

            assert success is True
            assert mock_post.called

            # Verify message format
            call_kwargs = mock_post.call_args[1]
            assert "chat_id" in call_kwargs["json"]
            assert "text" in call_kwargs["json"]
            text = call_kwargs["json"]["text"]
            assert "🔴 DOWN" in text
            assert "https://example.com" in text
            assert "Connection timeout" in text

    def test_notify_down_with_status_code(self, notifier):
        """Test down notification with status code."""
        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=False,
            status_code=500,
        )

        with patch("uptime_ping.notifier.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"ok": True}
            mock_post.return_value = mock_response

            notifier.notify_down(result)

            text = mock_post.call_args[1]["json"]["text"]
            assert "500" in text

    def test_notify_up_success(self, notifier):
        """Test sending recovery notification."""
        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=True,
            status_code=200,
            latency_ms=120.3,
        )

        with patch("uptime_ping.notifier.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"ok": True}
            mock_post.return_value = mock_response

            success = notifier.notify_up(result)

            assert success is True
            text = mock_post.call_args[1]["json"]["text"]
            assert "🟢 UP" in text
            assert "https://example.com" in text
            assert "200" in text
            assert "120ms" in text

    def test_notify_api_failure(self, notifier):
        """Test handling of Telegram API failure."""
        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=False,
            error="Down",
        )

        with patch("uptime_ping.notifier.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"ok": False}
            mock_post.return_value = mock_response

            success = notifier.notify_down(result)

            assert success is False

    def test_notify_network_error(self, notifier):
        """Test handling of network errors."""
        import requests

        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=False,
            error="Down",
        )

        with patch("uptime_ping.notifier.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Network error")

            success = notifier.notify_down(result)

            assert success is False

    def test_notify_http_error(self, notifier):
        """Test handling of HTTP errors."""
        import requests

        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=False,
            error="Down",
        )

        with patch("uptime_ping.notifier.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400")
            mock_post.return_value = mock_response

            success = notifier.notify_down(result)

            assert success is False

    def test_format_down_message_minimal(self, notifier):
        """Test formatting down message with minimal info."""
        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=False,
        )

        message = notifier._format_down_message(result)

        assert "🔴 DOWN: https://example.com" in message
        assert "2026-09-02T12:00:00+00:00" in message

    def test_format_up_message(self, notifier):
        """Test formatting up message."""
        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=True,
            status_code=200,
            latency_ms=95.7,
        )

        message = notifier._format_up_message(result)

        assert "🟢 UP: https://example.com" in message
        assert "Status: 200" in message
        assert "Latency: 96ms" in message  # Rounded

    def test_api_url_format(self, notifier):
        """Test API URL is correctly formatted."""
        assert notifier.token == "test-token"
        assert notifier.chat_id == "test-chat-id"

        expected_url = "https://api.telegram.org/bottest-token/sendMessage"
        assert notifier.API_URL.format(token=notifier.token) == expected_url
