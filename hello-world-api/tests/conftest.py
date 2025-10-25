"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_fixture() -> str:
    """Sample fixture for testing.

    Returns:
        str: Test value
    """
    return "test_value"
