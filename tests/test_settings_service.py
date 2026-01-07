import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from schemas.imports import MainGoals
from schemas.settings import (
    DevicePlatform,
    DevicePushState,
    DeviceStatus,
    ProfileUpdates,
    SettingsRequest,
)
from services.settings_service import _compute_device_status, apply_settings_request


def test_device_status_disabled_when_preference_off():
    status = _compute_device_status(False, None)
    assert status == DeviceStatus.disabled


def test_device_status_needs_setup_when_preference_on_no_device():
    status = _compute_device_status(True, None)
    assert status == DeviceStatus.needs_setup


def test_device_status_enabled_with_permission_and_token():
    device_state = DevicePushState(
        device_id="device-1",
        platform=DevicePlatform.ios,
        permission_granted=True,
        push_token="token",
    )
    status = _compute_device_status(True, device_state)
    assert status == DeviceStatus.enabled


def test_settings_update_blocked_before_onboarding(monkeypatch):
    async def fake_retrieve_user_by_user_id(id: str):
        return SimpleNamespace(onboardingCompleted=False)

    monkeypatch.setattr(
        "services.settings_service.retrieve_user_by_user_id",
        fake_retrieve_user_by_user_id,
    )

    payload = SettingsRequest(
        profile_updates=ProfileUpdates(mainGoals=[MainGoals.Travel])
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(apply_settings_request("user-1", payload))

    assert exc.value.status_code == 409
