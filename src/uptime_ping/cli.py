"""CLI interface for uptime-ping."""

import sys
import time
from datetime import datetime, timezone
from typing import Optional

import click

from . import __version__
from .config import Config
from .storage import Storage, CheckResult, Endpoint
from .checker import Checker
from .notifier import Notifier


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """uptime-ping: Scheduled uptime monitor with Telegram alerts."""


@main.command()
@click.argument("url")
@click.option("--interval", "-i", default=300, type=int, help="Check interval in seconds")
@click.pass_context
def add(ctx: click.Context, url: str, interval: int) -> None:
    """Add a URL to monitor."""
    config = Config()
    storage = Storage(config.db_path)
    storage.add_endpoint(url, interval)
    click.echo(f"✓ Added {url} (interval: {interval}s)")


@main.command()
@click.argument("url")
@click.pass_context
def remove(ctx: click.Context, url: str) -> None:
    """Remove a URL from monitoring."""
    config = Config()
    storage = Storage(config.db_path)
    if storage.remove_endpoint(url):
        click.echo(f"✓ Removed {url}")
    else:
        click.echo(f"✗ {url} not found", err=True)
        sys.exit(1)


@main.command()
def list() -> None:
    """List monitored URLs."""
    config = Config()
    storage = Storage(config.db_path)
    endpoints = storage.list_endpoints()

    if not endpoints:
        click.echo("No endpoints configured. Use 'uptime-ping add <url>' to add one.")
        return

    for ep in endpoints:
        status = _format_status(ep)
        click.echo(f"{ep.url}  [{ep.interval}s]  {status}")


@main.command()
@click.option("--url", "-u", help="Check only this URL")
@click.option("--notify/--no-notify", default=True, help="Send Telegram alerts")
def check(url: Optional[str], notify: bool) -> None:
    """Run checks on monitored endpoints."""
    config = Config()
    storage = Storage(config.db_path)
    checker = Checker()

    notifier: Optional[Notifier] = None
    if notify and config.has_telegram_config():
        notifier = Notifier(config.telegram_token, config.telegram_chat_id)

    if url:
        endpoints = [storage.get_endpoint(url)]
        if not endpoints[0]:
            click.echo(f"✗ {url} not found", err=True)
            sys.exit(1)
    else:
        endpoints = storage.list_endpoints()

    if not endpoints:
        click.echo("No endpoints to check.")
        return

    for endpoint in endpoints:
        result = checker.check(endpoint.url)
        storage.save_check_result(result)
        storage.update_endpoint_status(
            result.url, result.is_up, result.status_code, result.checked_at
        )

        _print_result(result, endpoint)
        _maybe_notify(notifier, result, endpoint)


@main.command()
@click.option("--once/--loop", default=False, help="Run one check cycle then exit")
def daemon(once: bool) -> None:
    """Run continuous monitoring daemon."""
    config = Config()
    storage = Storage(config.db_path)
    checker = Checker()

    notifier: Optional[Notifier] = None
    if config.has_telegram_config():
        notifier = Notifier(config.telegram_token, config.telegram_chat_id)
        click.echo("✓ Telegram notifications enabled")
    else:
        click.echo("⚠ Telegram not configured - running without notifications")

    click.echo(f"Daemon started (db: {config.db_path})")

    try:
        while True:
            now = datetime.now(timezone.utc)
            due = storage.get_due_endpoints(now)

            if due:
                click.echo(f"[{now.isoformat()}] Checking {len(due)} endpoint(s)")

            for endpoint in due:
                result = checker.check(endpoint.url)
                storage.save_check_result(result)
                storage.update_endpoint_status(
                    result.url, result.is_up, result.status_code, result.checked_at
                )
                _print_result(result, endpoint)
                _maybe_notify(notifier, result, endpoint)

            if once:
                break

            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nDaemon stopped")


def _format_status(ep: Endpoint) -> str:
    """Format endpoint status for display."""
    if ep.is_up is None:
        return "⚪ not checked"
    if ep.is_up:
        parts = ["🟢 up"]
        if ep.last_status_code:
            parts.append(f"({ep.last_status_code})")
        return " ".join(parts)
    parts = ["🔴 down"]
    if ep.last_status_code:
        parts.append(f"({ep.last_status_code})")
    return " ".join(parts)


def _print_result(result: CheckResult, endpoint: Endpoint) -> None:
    """Print a check result to stdout."""
    if result.is_up:
        latency = f"{result.latency_ms:.0f}ms" if result.latency_ms is not None else ""
        click.echo(f"🟢 {result.url} - UP ({result.status_code}) {latency}".rstrip())
    else:
        err = result.error or f"status {result.status_code}"
        click.echo(f"🔴 {result.url} - DOWN ({err})")


def _maybe_notify(
    notifier: Optional[Notifier],
    result: CheckResult,
    endpoint: Endpoint,
) -> None:
    """Send notification if status changed."""
    if notifier is None:
        return

    # Notify on down
    if result.is_up is False:
        notifier.notify_down(result)
        return

    # Notify on recovery (was down, now up)
    if result.is_up and endpoint.is_up is False:
        notifier.notify_up(result)


if __name__ == "__main__":
    main()
