import asyncio
import pytest

from security.encrypting_jwt import create_jwt_token, decode_jwt_token


def test_jwt_round_trip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    token = create_jwt_token(
        access_token="access-123",
        user_id="user-1",
        user_type="USER",
        is_activated=True,
    )
    payload = asyncio.run(decode_jwt_token(token))
    assert payload["access_token"] == "access-123"
    assert payload["user_id"] == "user-1"
    assert payload["role"] == "member"
