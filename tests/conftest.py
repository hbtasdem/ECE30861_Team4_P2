"""Pytest configuration - imports fixtures from test_setup module."""

# Import all fixtures from test_setup module so pytest can discover them
from tests.test_setup import client, db, test_db, test_token  # noqa: F401
