from __future__ import annotations

from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from repositories.device_state_repo import get_device_state, upsert_device_state
from repositories.user_repo import unset_user_fields
from schemas.settings import (
    DevicePushState,
    DeviceStatus,
    NotificationView,
    ProfileUpdates,
    SettingsRequest,
    SettingsView,
)
from schemas.user_schema import (
    UserNotifications,
    UserNotificationPreference,
    UserOut,
    UserPersonalProfilingData,
    UserUpdate,
)
from services.user_service import (
    enqueue_user_data_cleanup,
    remove_user,
    retrieve_user_by_user_id,
    update_user_by_id,
)


def _has_profile_updates(profile_updates: ProfileUpdates) -> bool:
    return any(
        field is not None
        for field in [
            profile_updates.mainGoals,
            profile_updates.dailyPracticeTime,
            profile_updates.nativeLanguage,
            profile_updates.currentProficiency,
            profile_updates.learnerType,
        ]
    )


def _compute_device_status(
    preference_enabled: bool,
    device_state: Optional[DevicePushState],
) -> DeviceStatus:
    if not preference_enabled:
        return DeviceStatus.disabled
    if not device_state:
        return DeviceStatus.needs_setup
    if not device_state.permission_granted:
        return DeviceStatus.needs_setup
    if not device_state.push_token:
        return DeviceStatus.needs_setup
    return DeviceStatus.enabled


def _build_settings_view(
    user: UserOut,
    device_state: Optional[DevicePushState] = None,
) -> SettingsView:
    profile = user.userPersonalProfilingData
    primary_goals = []
    daily_practice_time = None
    profiling_native_language = None
    profiling_current_proficiency = None
    profiling_learner_type = None

    if profile:
        primary_goals = list(profile.mainGoals)
        daily_practice_time = profile.dailyPracticeTime
        profiling_native_language = profile.nativeLanguage
        profiling_current_proficiency = profile.currentProficiency
        profiling_learner_type = profile.learnerType

    preference_enabled = False
    if user.notifications and user.notifications.preference:
        preference_enabled = user.notifications.preference.enabled

    device_status = _compute_device_status(preference_enabled, device_state)

    notification_view = NotificationView(
        preference={"enabled": preference_enabled},
        device_state=device_state,
        this_device_status=device_status,
    )

    return SettingsView(
        primary_goals={"goals": primary_goals},
        study_availability={"dailyPracticeTime": daily_practice_time},
        profiling={
            "nativeLanguage": profiling_native_language,
            "currentProficiency": profiling_current_proficiency,
            "learnerType": profiling_learner_type,
        },
        notifications=notification_view,
    )


async def get_settings_view(user_id: str, device_id: Optional[str]) -> SettingsView:
    user = await retrieve_user_by_user_id(id=user_id)
    if not user.onboardingCompleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding to access settings.",
        )

    device_state = None
    if device_id:
        device_state = await get_device_state(user_id=user_id, device_id=device_id)

    return _build_settings_view(user, device_state)


async def apply_settings_request(
    user_id: str,
    payload: SettingsRequest,
) -> Optional[SettingsView]:
    user = await retrieve_user_by_user_id(id=user_id)

    if payload.account.delete_account:
        await remove_user(user_id=user_id)
        return None

    if payload.account.reset_account:
        await reset_user_profile(user_id=user_id)
        return None

    if not user.onboardingCompleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding to update settings.",
        )

    device_state = None
    if payload.notifications.device_state:
        device_state = await upsert_device_state(
            user_id=user_id,
            payload=payload.notifications.device_state,
        )

    if payload.notifications.preference.enabled is not None:
        notifications = user.notifications or UserNotifications(
            preference=UserNotificationPreference(enabled=False)
        )
        notifications.preference.enabled = payload.notifications.preference.enabled
        user = await update_user_by_id(
            driver_id=user_id,
            driver_data=UserUpdate(notifications=notifications),
        )

    if _has_profile_updates(payload.profile_updates):
        user = await _apply_profile_updates(user, payload.profile_updates)

    return _build_settings_view(user, device_state)


async def reset_user_profile(user_id: str) -> UserOut:
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    filter_dict = {"_id": ObjectId(user_id)}
    user_out = await unset_user_fields(
        filter_dict=filter_dict,
        field_names=["userPersonalProfilingData"],
    )
    notifications = UserNotifications(
        preference=UserNotificationPreference(enabled=False)
    )
    user_out = await update_user_by_id(
        driver_id=user_id,
        driver_data=UserUpdate(notifications=notifications),
    )
    enqueue_user_data_cleanup(user_id)
    return user_out




async def _apply_profile_updates(
    user: UserOut,
    profile_updates: ProfileUpdates,
) -> UserOut:
    if not user.userPersonalProfilingData:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding to update profile settings.",
        )

    if profile_updates.mainGoals is not None and len(profile_updates.mainGoals) == 0:
        return await reset_user_profile(user_id=user.id)

    profile_data = user.userPersonalProfilingData.model_dump()

    if profile_updates.mainGoals is not None:
        profile_data["mainGoals"] = profile_updates.mainGoals
    if profile_updates.dailyPracticeTime is not None:
        profile_data["dailyPracticeTime"] = profile_updates.dailyPracticeTime
    if profile_updates.nativeLanguage is not None:
        profile_data["nativeLanguage"] = profile_updates.nativeLanguage
    if profile_updates.currentProficiency is not None:
        profile_data["currentProficiency"] = profile_updates.currentProficiency
    if profile_updates.learnerType is not None:
        profile_data["learnerType"] = profile_updates.learnerType

    updated_profile = UserPersonalProfilingData(**profile_data)

    return await update_user_by_id(
        driver_id=user.id,
        driver_data=UserUpdate(userPersonalProfilingData=updated_profile),
    )


async def sync_device_state(
    user_id: str,
    payload: DevicePushState,
) -> NotificationView:
    user = await retrieve_user_by_user_id(id=user_id)
    device_state = await upsert_device_state(user_id=user_id, payload=payload)

    preference_enabled = False
    if user.notifications and user.notifications.preference:
        preference_enabled = user.notifications.preference.enabled

    return NotificationView(
        preference={"enabled": preference_enabled},
        device_state=device_state,
        this_device_status=_compute_device_status(preference_enabled, device_state),
    )
