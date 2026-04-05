"""
Shared fixtures for backend tests.
Uses a temporary in-memory or file-based SQLite DB to avoid touching production data.
"""
import os
import sys
import pytest

# Ensure backend/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set test environment variables BEFORE importing app modules
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
os.environ.setdefault("TESTING", "1")


@pytest.fixture(scope="session")
def app():
    """Create FastAPI test app."""
    from main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """Create a TestClient for the FastAPI app."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_token():
    """Generate a valid JWT token for testing."""
    from auth import create_access_token
    return create_access_token({
        "userId": "test_user_001",
        "email": "test@pharma.local",
        "role": "admin",
        "name": "Test Admin"
    })


@pytest.fixture
def auth_headers(auth_token):
    """Return headers with valid Bearer token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
