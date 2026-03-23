"""Shared test fixtures."""

import pytest

from pyroblox.client import RobloxClient


@pytest.fixture
def client() -> RobloxClient:
    """A RobloxClient pointed at a mock base URL (overridden by pytest-httpx)."""
    return RobloxClient()
