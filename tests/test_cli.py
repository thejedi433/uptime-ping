"""Tests for CLI module."""

import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
from uptime_ping.cli import main
from uptime_ping.storage import Endpoint


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config with temporary database."""
        with patch("uptime_ping.cli.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.db_path = tmp_path / "test.db"
            mock_config.telegram_token = None
            mock_config.telegram_chat_id = None
            mock_config.has_telegram_config.return_value = False
            mock_config_class.return_value = mock_config
            yield mock_config

    def test_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_add_endpoint(self, runner, mock_config):
        """Test adding an endpoint."""
        result = runner.invoke(main, ["add", "https://example.com"])

        assert result.exit_code == 0
        assert "✓ Added" in result.output
        assert "https://example.com" in result.output

    def test_add_endpoint_with_interval(self, runner, mock_config):
        """Test adding endpoint with custom interval."""
        result = runner.invoke(main, ["add", "https://example.com", "--interval", "60"])

        assert result.exit_code == 0
        assert "60s" in result.output

    def test_remove_endpoint_exists(self, runner, mock_config):
        """Test removing an existing endpoint."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.remove_endpoint.return_value = True
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["remove", "https://example.com"])

            assert result.exit_code == 0
            assert "✓ Removed" in result.output

    def test_remove_endpoint_not_exists(self, runner, mock_config):
        """Test removing a non-existent endpoint."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.remove_endpoint.return_value = False
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["remove", "https://example.com"])

            assert result.exit_code == 1
            assert "not found" in result.output

    def test_list_endpoints_empty(self, runner, mock_config):
        """Test listing endpoints when none exist."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.list_endpoints.return_value = []
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["list"])

            assert result.exit_code == 0
            assert "No endpoints configured" in result.output

    def test_list_endpoints(self, runner, mock_config):
        """Test listing endpoints."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.list_endpoints.return_value = [
                Endpoint(url="https://a.com", interval=60, is_up=True, last_status_code=200),
                Endpoint(url="https://b.com", interval=120, is_up=False, last_status_code=500),
                Endpoint(url="https://c.com", interval=180, is_up=None),
            ]
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["list"])

            assert result.exit_code == 0
            assert "https://a.com" in result.output
            assert "60s" in result.output
            assert "🟢 up" in result.output
            assert "https://b.com" in result.output
            assert "🔴 down" in result.output
            assert "https://c.com" in result.output
            assert "not checked" in result.output

    def test_check_all_endpoints(self, runner, mock_config):
        """Test checking all endpoints."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Checker") as mock_checker_class:

            mock_storage = Mock()
            mock_storage.list_endpoints.return_value = [
                Endpoint(url="https://example.com", interval=60, is_up=None),
            ]
            mock_storage_class.return_value = mock_storage

            mock_checker = Mock()
            from uptime_ping.storage import CheckResult
            mock_checker.check.return_value = CheckResult(
                url="https://example.com",
                checked_at="2026-09-02T12:00:00+00:00",
                is_up=True,
                status_code=200,
                latency_ms=100.0,
            )
            mock_checker_class.return_value = mock_checker

            result = runner.invoke(main, ["check"])

            assert result.exit_code == 0
            assert "🟢" in result.output
            assert "UP" in result.output

    def test_check_specific_url(self, runner, mock_config):
        """Test checking a specific URL."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Checker") as mock_checker_class:

            mock_storage = Mock()
            mock_storage.get_endpoint.return_value = Endpoint(
                url="https://example.com", interval=60
            )
            mock_storage_class.return_value = mock_storage

            mock_checker = Mock()
            from uptime_ping.storage import CheckResult
            mock_checker.check.return_value = CheckResult(
                url="https://example.com",
                checked_at="2026-09-02T12:00:00+00:00",
                is_up=True,
                status_code=200,
            )
            mock_checker_class.return_value = mock_checker

            result = runner.invoke(main, ["check", "--url", "https://example.com"])

            assert result.exit_code == 0
            mock_storage.get_endpoint.assert_called_once_with("https://example.com")

    def test_check_url_not_found(self, runner, mock_config):
        """Test checking a URL that doesn't exist."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.get_endpoint.return_value = None
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["check", "--url", "https://example.com"])

            assert result.exit_code == 1
            assert "not found" in result.output

    def test_check_no_endpoints(self, runner, mock_config):
        """Test checking when no endpoints exist."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.list_endpoints.return_value = []
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["check"])

            assert result.exit_code == 0
            assert "No endpoints to check" in result.output

    def test_check_with_notification(self, runner, mock_config):
        """Test check with notifications enabled."""
        mock_config.has_telegram_config.return_value = True
        mock_config.telegram_token = "token"
        mock_config.telegram_chat_id = "chat-id"

        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Checker") as mock_checker_class, \
             patch("uptime_ping.cli.Notifier") as mock_notifier_class:

            mock_storage = Mock()
            mock_storage.list_endpoints.return_value = [
                Endpoint(url="https://example.com", interval=60, is_up=None),
            ]
            mock_storage_class.return_value = mock_storage

            mock_checker = Mock()
            from uptime_ping.storage import CheckResult
            mock_checker.check.return_value = CheckResult(
                url="https://example.com",
                checked_at="2026-09-02T12:00:00+00:00",
                is_up=False,
                error="Down",
            )
            mock_checker_class.return_value = mock_checker

            mock_notifier = Mock()
            mock_notifier_class.return_value = mock_notifier

            result = runner.invoke(main, ["check"])

            assert result.exit_code == 0
            mock_notifier.notify_down.assert_called_once()

    def test_check_without_notification(self, runner, mock_config):
        """Test check with notifications disabled."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Checker") as mock_checker_class:

            mock_storage = Mock()
            mock_storage.list_endpoints.return_value = [
                Endpoint(url="https://example.com", interval=60, is_up=None),
            ]
            mock_storage_class.return_value = mock_storage

            mock_checker = Mock()
            from uptime_ping.storage import CheckResult
            mock_checker.check.return_value = CheckResult(
                url="https://example.com",
                checked_at="2026-09-02T12:00:00+00:00",
                is_up=True,
                status_code=200,
            )
            mock_checker_class.return_value = mock_checker

            result = runner.invoke(main, ["check", "--no-notify"])

            assert result.exit_code == 0

    def test_daemon_continuous(self, runner, mock_config):
        """Test daemon in continuous mode (without --once)."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Checker") as mock_checker_class, \
             patch("uptime_ping.cli.time") as mock_time:

            from datetime import datetime, timezone
            mock_storage = Mock()
            mock_storage.get_due_endpoints.return_value = []
            mock_storage_class.return_value = mock_storage

            # Make time.sleep raise an exception after first call to break the loop
            mock_time.sleep.side_effect = [None, KeyboardInterrupt()]

            result = runner.invoke(main, ["daemon"])

            assert result.exit_code == 0
            # Verify sleep was called (meaning we're in continuous mode)
            assert mock_time.sleep.called

    def test_daemon_once(self, runner, mock_config):
        """Test daemon with --once flag."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Checker") as mock_checker_class, \
             patch("uptime_ping.cli.time") as mock_time:

            from datetime import datetime, timezone
            mock_storage = Mock()
            mock_storage.get_due_endpoints.return_value = [
                Endpoint(url="https://example.com", interval=60, is_up=None),
            ]
            mock_storage_class.return_value = mock_storage

            mock_checker = Mock()
            from uptime_ping.storage import CheckResult
            mock_checker.check.return_value = CheckResult(
                url="https://example.com",
                checked_at="2026-09-02T12:00:00+00:00",
                is_up=True,
                status_code=200,
            )
            mock_checker_class.return_value = mock_checker

            result = runner.invoke(main, ["daemon", "--once"])

            assert result.exit_code == 0
            assert "Daemon started" in result.output
            # Verify sleep was NOT called (meaning we broke out of loop)
            assert not mock_time.sleep.called

    def test_daemon_no_telegram(self, runner, mock_config):
        """Test daemon without Telegram configuration."""
        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.time.sleep"):

            mock_storage = Mock()
            mock_storage.get_due_endpoints.return_value = []
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["daemon", "--once"])

            assert result.exit_code == 0
            assert "Telegram not configured" in result.output

    def test_daemon_with_telegram(self, runner, mock_config):
        """Test daemon with Telegram configuration."""
        mock_config.has_telegram_config.return_value = True
        mock_config.telegram_token = "token"
        mock_config.telegram_chat_id = "chat-id"

        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Notifier") as mock_notifier_class, \
             patch("uptime_ping.cli.time.sleep"):

            mock_storage = Mock()
            mock_storage.get_due_endpoints.return_value = []
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(main, ["daemon", "--once"])

            assert result.exit_code == 0
            assert "Telegram notifications enabled" in result.output

    def test_format_status_not_checked(self):
        """Test formatting status for unchecked endpoint."""
        from uptime_ping.cli import _format_status

        endpoint = Endpoint(url="https://example.com", interval=60)
        status = _format_status(endpoint)

        assert "not checked" in status

    def test_format_status_up(self):
        """Test formatting status for up endpoint."""
        from uptime_ping.cli import _format_status

        endpoint = Endpoint(
            url="https://example.com",
            interval=60,
            is_up=True,
            last_status_code=200
        )
        status = _format_status(endpoint)

        assert "🟢 up" in status
        assert "200" in status

    def test_format_status_down(self):
        """Test formatting status for down endpoint."""
        from uptime_ping.cli import _format_status

        endpoint = Endpoint(
            url="https://example.com",
            interval=60,
            is_up=False,
            last_status_code=500
        )
        status = _format_status(endpoint)

        assert "🔴 down" in status
        assert "500" in status

    def test_notify_on_recovery(self, runner, mock_config):
        """Test notification sent on recovery."""
        mock_config.has_telegram_config.return_value = True
        mock_config.telegram_token = "token"
        mock_config.telegram_chat_id = "chat-id"

        with patch("uptime_ping.cli.Storage") as mock_storage_class, \
             patch("uptime_ping.cli.Checker") as mock_checker_class, \
             patch("uptime_ping.cli.Notifier") as mock_notifier_class:

            # Endpoint was previously down
            mock_storage = Mock()
            mock_storage.list_endpoints.return_value = [
                Endpoint(url="https://example.com", interval=60, is_up=False),
            ]
            mock_storage_class.return_value = mock_storage

            mock_checker = Mock()
            from uptime_ping.storage import CheckResult
            # Now it's up
            mock_checker.check.return_value = CheckResult(
                url="https://example.com",
                checked_at="2026-09-02T12:00:00+00:00",
                is_up=True,
                status_code=200,
            )
            mock_checker_class.return_value = mock_checker

            mock_notifier = Mock()
            mock_notifier_class.return_value = mock_notifier

            result = runner.invoke(main, ["check"])

            assert result.exit_code == 0
            mock_notifier.notify_up.assert_called_once()
