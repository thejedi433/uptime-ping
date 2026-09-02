"""Tests for checker module."""

import pytest
from unittest.mock import patch, Mock
from uptime_ping.checker import Checker


class TestChecker:
    """Test HTTP health checker."""

    @pytest.fixture
    def checker(self):
        """Create a checker instance."""
        return Checker(timeout=5.0)

    def test_check_success(self, checker):
        """Test successful health check."""
        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = checker.check("https://example.com")

            assert result.url == "https://example.com"
            assert result.is_up is True
            assert result.status_code == 200
            assert result.error is None
            assert result.latency_ms is not None

    def test_check_success_codes(self, checker):
        """Test various success status codes."""
        for code in [200, 201, 202, 204, 301, 302]:
            with patch("uptime_ping.checker.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = code
                mock_get.return_value = mock_response

                result = checker.check("https://example.com")
                assert result.is_up is True

    def test_check_failure_codes(self, checker):
        """Test failure status codes."""
        for code in [400, 401, 403, 404, 500, 503]:
            with patch("uptime_ping.checker.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = code
                mock_get.return_value = mock_response

                result = checker.check("https://example.com")
                assert result.is_up is False

    def test_check_timeout(self, checker):
        """Test timeout handling."""
        import requests

        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

            result = checker.check("https://example.com")

            assert result.is_up is False
            assert "Timeout" in result.error
            assert result.status_code is None

    def test_check_connection_error(self, checker):
        """Test connection error handling."""
        import requests

        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

            result = checker.check("https://example.com")

            assert result.is_up is False
            assert "Connection error" in result.error
            assert result.status_code is None

    def test_check_request_exception(self, checker):
        """Test generic request exception handling."""
        import requests

        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Unknown error")

            result = checker.check("https://example.com")

            assert result.is_up is False
            assert "Request failed" in result.error

    def test_check_custom_timeout(self):
        """Test checker with custom timeout."""
        checker = Checker(timeout=30.0)

        import requests

        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Timed out")

            checker.check("https://example.com")

            # Verify timeout was passed to requests
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["timeout"] == 30.0

    def test_check_custom_success_codes(self):
        """Test checker with custom success codes."""
        checker = Checker(success_codes=(200, 201))

        with patch("uptime_ping.checker.requests.get") as mock_get:
            # 202 should fail with custom codes
            mock_response = Mock()
            mock_response.status_code = 202
            mock_get.return_value = mock_response

            result = checker.check("https://example.com")
            assert result.is_up is False

    def test_check_latency_measurement(self, checker):
        """Test that latency is measured."""
        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = checker.check("https://example.com")

            assert result.latency_ms is not None
            assert result.latency_ms > 0

    def test_short_error_truncation(self, checker):
        """Test that long error messages are truncated."""
        import requests

        long_error = "x" * 300
        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException(long_error)

            result = checker.check("https://example.com")

            assert len(result.error) <= 216  # "Request failed: " (16) + 200 chars max

    def test_checked_at_timestamp(self, checker):
        """Test that checked_at is set."""
        with patch("uptime_ping.checker.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = checker.check("https://example.com")

            assert result.checked_at is not None
            assert "T" in result.checked_at  # ISO format
