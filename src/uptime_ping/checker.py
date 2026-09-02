"""URL checker - performs HTTP health checks."""

import time
from datetime import datetime, timezone
from typing import Optional, Tuple
import requests

from .storage import CheckResult


class Checker:
    """HTTP health checker for endpoints."""

    def __init__(
        self,
        timeout: float = 10.0,
        success_codes: Tuple[int, ...] = (200, 201, 202, 204, 301, 302),
    ):
        self.timeout = timeout
        self.success_codes = success_codes

    def check(self, url: str) -> CheckResult:
        """Perform a health check on a URL.

        Returns a CheckResult with is_up=True if the HTTP status is in success_codes.
        """
        checked_at = datetime.now(timezone.utc).isoformat()

        try:
            start = time.monotonic()
            response = requests.get(url, timeout=self.timeout, allow_redirects=False)
            latency_ms = (time.monotonic() - start) * 1000

            is_up = response.status_code in self.success_codes
            return CheckResult(
                url=url,
                checked_at=checked_at,
                is_up=is_up,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
            )
        except requests.exceptions.Timeout:
            return CheckResult(
                url=url,
                checked_at=checked_at,
                is_up=False,
                error=f"Timeout after {self.timeout}s",
            )
        except requests.exceptions.ConnectionError as e:
            return CheckResult(
                url=url,
                checked_at=checked_at,
                is_up=False,
                error=f"Connection error: {self._short_error(e)}",
            )
        except requests.exceptions.RequestException as e:
            return CheckResult(
                url=url,
                checked_at=checked_at,
                is_up=False,
                error=f"Request failed: {self._short_error(e)}",
            )

    def _short_error(self, exc: Exception) -> str:
        """Truncate long error messages."""
        msg = str(exc)
        return msg[:200] if len(msg) > 200 else msg
