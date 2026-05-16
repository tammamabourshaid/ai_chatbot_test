"""
conftest.py

Shared pytest configuration and fixtures.
"""
import pytest
from chatbot_client import send_message


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m not slow')"
    )


@pytest.fixture(scope="session", autouse=True)
def require_server():
    result = send_message("ping")
    status = result.get("status", 0)
    if status == 0:
        pytest.skip("Chatbot server unreachable -- set APP_URL in .env")
    if status == 401:
        pytest.skip("Authentication failed -- set SESSION_TOKEN in .env")
    if status == 404:
        pytest.skip("Endpoint not found -- check APP_URL in .env")
