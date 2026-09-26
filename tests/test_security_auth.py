import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import repositories.tokens_repo as tokens_repo
import security.auth as auth

CREDENTIALS = SimpleNamespace(credentials="header.payload.signature")
TOKEN_ID = "64b000000000000000000002"


def _verify():
    return asyncio.run(auth.verify_token_user_role(CREDENTIALS))


def test_revoked_token_gets_a_plain_401(monkeypatch):
    async def fake_decode(token):
        return {"access_token": TOKEN_ID}

    async def fake_lookup(accessToken):
        return None

    monkeypatch.setattr(auth, "decode_jwt_token", fake_decode)
    monkeypatch.setattr(auth, "get_access_tokens", fake_lookup)
    with pytest.raises(HTTPException) as caught:
        _verify()
    assert caught.value.status_code == 401
    assert caught.value.detail == "Invalid token"


def test_expired_jwt_gets_a_plain_401(monkeypatch):
    async def fake_decode(token):
        return None

    monkeypatch.setattr(auth, "decode_jwt_token", fake_decode)
    with pytest.raises(HTTPException) as caught:
        _verify()
    assert caught.value.status_code == 401
    assert caught.value.detail == "Invalid token"


def test_live_token_passes(monkeypatch):
    stored = SimpleNamespace(userId="64b000000000000000000001")

    async def fake_decode(token):
        return {"access_token": TOKEN_ID}

    async def fake_lookup(accessToken):
        return stored

    async def fake_user(id):
        return SimpleNamespace(id=id)

    monkeypatch.setattr(auth, "decode_jwt_token", fake_decode)
    monkeypatch.setattr(auth, "get_access_tokens", fake_lookup)
    monkeypatch.setattr(auth, "retrieve_user_by_user_id", fake_user)
    assert _verify() is stored


def test_missing_access_token_is_none(monkeypatch):
    async def find_one(filter):
        return None

    monkeypatch.setattr(
        tokens_repo, "db", SimpleNamespace(accessToken=SimpleNamespace(find_one=find_one))
    )
    assert asyncio.run(tokens_repo.get_access_tokens(TOKEN_ID)) is None
