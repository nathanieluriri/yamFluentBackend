import asyncio
import pytest
from types import SimpleNamespace

import services.session_service as session_service


def test_delete_sessions_for_user_deletes_all(monkeypatch):
    batches = [
        [SimpleNamespace(id="s1"), SimpleNamespace(id="s2")],
        [],
    ]
    removed = []

    async def fake_retrieve_sessions(user_id, start=0, stop=100, filters=None):
        return batches.pop(0)

    async def fake_remove_session(session_id, user_id):
        removed.append((session_id, user_id))

    monkeypatch.setattr(session_service, "retrieve_sessions", fake_retrieve_sessions)
    monkeypatch.setattr(session_service, "remove_session", fake_remove_session)

    deleted = asyncio.run(
        session_service.delete_sessions_for_user("user-1", batch_size=2)
    )

    assert deleted == 2
    assert removed == [("s1", "user-1"), ("s2", "user-1")]
