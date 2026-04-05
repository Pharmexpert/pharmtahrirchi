"""Tests for authentication module."""
import pytest
from auth import create_access_token, verify_token


class TestJWT:
    def test_create_and_verify_token(self):
        """Token creation and verification round-trip."""
        data = {"userId": "user_1", "email": "a@b.com", "role": "admin", "name": "Test"}
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)

        payload = verify_token(token)
        assert payload is not None
        assert payload["userId"] == "user_1"
        assert payload["email"] == "a@b.com"
        assert payload["role"] == "admin"

    def test_verify_invalid_token(self):
        """Invalid tokens should return None."""
        assert verify_token("garbage-token") is None
        assert verify_token("") is None
        assert verify_token("eyJ.invalid.token") is None

    def test_dev_token_removed(self):
        """The dev-token bypass must NOT exist."""
        result = verify_token("dev-token")
        assert result is None, "dev-token bypass should be removed!"

    def test_token_contains_expiry(self):
        """Token payload should include exp claim."""
        token = create_access_token({"userId": "u1"})
        payload = verify_token(token)
        assert "exp" in payload


class TestAuthEndpoints:
    def test_register_missing_fields(self, client):
        """Registration with missing fields should return 400."""
        res = client.post("/api/auth/register", json={"email": "x@x.com"})
        assert res.status_code == 400

    def test_login_missing_email(self, client):
        """Login without email should return 400."""
        res = client.post("/api/auth/login", json={"password": "test"})
        assert res.status_code == 400

    def test_login_wrong_credentials(self, client):
        """Login with invalid credentials should return 401."""
        res = client.post("/api/auth/login", json={"email": "nonexistent@x.com", "password": "wrong"})
        assert res.status_code == 401

    def test_auth_me_no_token(self, client):
        """GET /api/auth/me without token should return 401/403."""
        res = client.get("/api/auth/me")
        assert res.status_code in (401, 403)

    def test_google_auth_no_credential(self, client):
        """Google auth without credential should return 400."""
        res = client.post("/api/auth/google", json={})
        assert res.status_code == 400

    def test_forgot_password_nonexistent(self, client):
        """Forgot password for nonexistent user should still return success (security)."""
        res = client.post("/api/auth/forgot-password", json={"email": "nobody@x.com"})
        assert res.status_code == 200
        assert res.json()["success"] is True
