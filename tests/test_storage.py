"""Tests for storage module."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uptime_ping.storage import Storage, Endpoint, CheckResult


class TestStorage:
    """Test SQLite storage operations."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create a storage instance with temporary database."""
        db_path = tmp_path / "test.db"
        return Storage(db_path)

    def test_add_endpoint(self, storage):
        """Test adding a new endpoint."""
        endpoint = storage.add_endpoint("https://example.com", interval=60)

        assert endpoint.url == "https://example.com"
        assert endpoint.interval == 60
        assert endpoint.last_checked is None
        assert endpoint.is_up is None

    def test_add_endpoint_default_interval(self, storage):
        """Test adding endpoint with default interval."""
        endpoint = storage.add_endpoint("https://example.com")

        assert endpoint.interval == 300

    def test_add_endpoint_duplicate(self, storage):
        """Test adding duplicate endpoint updates it."""
        storage.add_endpoint("https://example.com", interval=60)
        endpoint = storage.add_endpoint("https://example.com", interval=120)

        assert endpoint.interval == 120

    def test_remove_endpoint_exists(self, storage):
        """Test removing an existing endpoint."""
        storage.add_endpoint("https://example.com")
        result = storage.remove_endpoint("https://example.com")

        assert result is True
        assert storage.get_endpoint("https://example.com") is None

    def test_remove_endpoint_not_exists(self, storage):
        """Test removing a non-existent endpoint."""
        result = storage.remove_endpoint("https://example.com")

        assert result is False

    def test_get_endpoint_exists(self, storage):
        """Test getting an existing endpoint."""
        storage.add_endpoint("https://example.com", interval=120)
        endpoint = storage.get_endpoint("https://example.com")

        assert endpoint is not None
        assert endpoint.url == "https://example.com"
        assert endpoint.interval == 120

    def test_get_endpoint_not_exists(self, storage):
        """Test getting a non-existent endpoint."""
        endpoint = storage.get_endpoint("https://example.com")

        assert endpoint is None

    def test_list_endpoints_empty(self, storage):
        """Test listing endpoints when none exist."""
        endpoints = storage.list_endpoints()

        assert endpoints == []

    def test_list_endpoints(self, storage):
        """Test listing multiple endpoints."""
        storage.add_endpoint("https://b.com", interval=60)
        storage.add_endpoint("https://a.com", interval=120)
        storage.add_endpoint("https://c.com", interval=180)

        endpoints = storage.list_endpoints()

        assert len(endpoints) == 3
        # Should be sorted by URL
        assert endpoints[0].url == "https://a.com"
        assert endpoints[1].url == "https://b.com"
        assert endpoints[2].url == "https://c.com"

    def test_update_endpoint_status(self, storage):
        """Test updating endpoint status."""
        storage.add_endpoint("https://example.com")
        checked_at = datetime.now(timezone.utc).isoformat()

        storage.update_endpoint_status("https://example.com", True, 200, checked_at)
        endpoint = storage.get_endpoint("https://example.com")

        assert endpoint.is_up is True
        assert endpoint.last_status_code == 200
        assert endpoint.last_checked == checked_at

    def test_save_check_result(self, storage):
        """Test saving a check result."""
        storage.add_endpoint("https://example.com")

        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=True,
            status_code=200,
            latency_ms=150.5,
        )
        storage.save_check_result(result)

        history = storage.get_check_history("https://example.com")
        assert len(history) == 1
        assert history[0].url == "https://example.com"
        assert history[0].is_up is True
        assert history[0].status_code == 200
        assert history[0].latency_ms == 150.5

    def test_save_check_result_with_error(self, storage):
        """Test saving a check result with error."""
        storage.add_endpoint("https://example.com")

        result = CheckResult(
            url="https://example.com",
            checked_at="2026-09-02T12:00:00+00:00",
            is_up=False,
            error="Connection timeout",
        )
        storage.save_check_result(result)

        history = storage.get_check_history("https://example.com")
        assert len(history) == 1
        assert history[0].is_up is False
        assert history[0].error == "Connection timeout"

    def test_get_check_history_limit(self, storage):
        """Test getting check history with limit."""
        storage.add_endpoint("https://example.com")

        # Add 10 check results
        for i in range(10):
            result = CheckResult(
                url="https://example.com",
                checked_at=f"2026-09-02T{12+i:02d}:00:00+00:00",
                is_up=True,
                status_code=200,
            )
            storage.save_check_result(result)

        # Get last 5
        history = storage.get_check_history("https://example.com", limit=5)
        assert len(history) == 5

    def test_get_check_history_empty(self, storage):
        """Test getting check history for URL with no checks."""
        history = storage.get_check_history("https://example.com")

        assert history == []

    def test_get_due_endpoints_never_checked(self, storage):
        """Test getting endpoints that have never been checked."""
        storage.add_endpoint("https://example.com")
        storage.add_endpoint("https://test.com")

        now = datetime.now(timezone.utc)
        due = storage.get_due_endpoints(now)

        assert len(due) == 2

    def test_get_due_endpoints_overdue(self, storage):
        """Test getting endpoints that are overdue."""
        storage.add_endpoint("https://example.com", interval=60)

        # Set last_checked to 2 minutes ago (interval is 60s)
        two_minutes_ago = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        storage.update_endpoint_status("https://example.com", True, 200, two_minutes_ago)

        now = datetime.now(timezone.utc)
        due = storage.get_due_endpoints(now)

        assert len(due) == 1
        assert due[0].url == "https://example.com"

    def test_get_due_endpoints_not_due(self, storage):
        """Test getting endpoints that are not yet due."""
        storage.add_endpoint("https://example.com", interval=300)

        # Set last_checked to 1 minute ago (interval is 300s = 5min)
        one_minute_ago = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        storage.update_endpoint_status("https://example.com", True, 200, one_minute_ago)

        now = datetime.now(timezone.utc)
        due = storage.get_due_endpoints(now)

        assert len(due) == 0

    def test_get_due_endpoints_mixed(self, storage):
        """Test getting due endpoints with mixed states."""
        storage.add_endpoint("https://due.com", interval=60)
        storage.add_endpoint("https://not-due.com", interval=300)
        storage.add_endpoint("https://never-checked.com", interval=60)

        # Make one overdue
        two_minutes_ago = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        storage.update_endpoint_status("https://due.com", True, 200, two_minutes_ago)

        # Make one not due yet
        one_minute_ago = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        storage.update_endpoint_status("https://not-due.com", True, 200, one_minute_ago)

        now = datetime.now(timezone.utc)
        due = storage.get_due_endpoints(now)

        assert len(due) == 2
        urls = [ep.url for ep in due]
        assert "https://due.com" in urls
        assert "https://never-checked.com" in urls
        assert "https://not-due.com" not in urls
