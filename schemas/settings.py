from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, AliasChoices

from schemas.imports import (
    CurrentProficiency,
    DailyPracticeTime,
    LearnerType,
    MainGoals,
    NativeLanguage,
)


class AccountAction(BaseModel):
    delete_account: bool = Field(
        default=False,
        validation_alias=AliasChoices("delete_account", "deleteAccount"),
        serialization_alias="deleteAccount",
    )
    reset_account: bool = Field(
        default=False,
        validation_alias=AliasChoices("reset_account", "resetAccount"),
        serialization_alias="resetAccount",
    )


class ProfileUpdates(BaseModel):
    mainGoals: Optional[List[MainGoals]] = Field(
        default=None,
        validation_alias=AliasChoices("mainGoals", "goals", "primary_goals"),
        serialization_alias="mainGoals",
    )
    dailyPracticeTime: Optional[DailyPracticeTime] = Field(
        default=None,
        validation_alias=AliasChoices(
            "dailyPracticeTime",
            "daily_practice_time",
            "daily_hours",
        ),
        serialization_alias="dailyPracticeTime",
    )
    nativeLanguage: Optional[NativeLanguage] = Field(
        default=None,
        validation_alias=AliasChoices("nativeLanguage", "native_language"),
        serialization_alias="nativeLanguage",
    )
    currentProficiency: Optional[CurrentProficiency] = Field(
        default=None,
        validation_alias=AliasChoices("currentProficiency", "current_proficiency"),
        serialization_alias="currentProficiency",
    )
    learnerType: Optional[LearnerType] = Field(
        default=None,
        validation_alias=AliasChoices("learnerType", "learner_type"),
        serialization_alias="learnerType",
    )


class PushPreference(BaseModel):
    enabled: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("enabled", "is_enabled"),
        serialization_alias="enabled",
    )


class DevicePlatform(str, Enum):
    ios = "ios"
    android = "android"
    web = "web"


class DevicePushState(BaseModel):
    device_id: str = Field(
        validation_alias=AliasChoices("device_id", "deviceId"),
        serialization_alias="deviceId",
    )
    platform: DevicePlatform
    permission_granted: bool = Field(
        default=False,
        validation_alias=AliasChoices("permission_granted", "permissionGranted"),
        serialization_alias="permissionGranted",
    )
    push_token: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("push_token", "pushToken"),
        serialization_alias="pushToken",
    )
    last_synced_at: Optional[datetime] = Field(
        default=None,
        validation_alias=AliasChoices("last_synced_at", "lastSyncedAt"),
        serialization_alias="lastSyncedAt",
    )


class NotificationBlock(BaseModel):
    preference: PushPreference = Field(default_factory=PushPreference)
    device_state: Optional[DevicePushState] = Field(
        default=None,
        validation_alias=AliasChoices("device_state", "deviceState"),
        serialization_alias="deviceState",
    )


class SettingsRequest(BaseModel):
    account: AccountAction = Field(default_factory=AccountAction)
    profile_updates: ProfileUpdates = Field(
        default_factory=ProfileUpdates,
        validation_alias=AliasChoices("profile_updates", "profileUpdates"),
        serialization_alias="profileUpdates",
    )
    notifications: NotificationBlock = Field(default_factory=NotificationBlock)


class PrimaryGoalsView(BaseModel):
    goals: List[MainGoals] = Field(default_factory=list)


class StudyAvailabilityView(BaseModel):
    dailyPracticeTime: Optional[DailyPracticeTime] = None


class ProfilingView(BaseModel):
    nativeLanguage: Optional[NativeLanguage] = None
    currentProficiency: Optional[CurrentProficiency] = None
    learnerType: Optional[LearnerType] = None


class PushPreferenceView(BaseModel):
    enabled: bool = False


class DeviceStatus(str, Enum):
    enabled = "enabled"
    needs_setup = "needs_setup"
    disabled = "disabled"


class DevicePushStateView(DevicePushState):
    pass


class NotificationView(BaseModel):
    preference: PushPreferenceView = Field(default_factory=PushPreferenceView)
    device_state: Optional[DevicePushStateView] = None
    this_device_status: DeviceStatus = DeviceStatus.disabled


class SettingsView(BaseModel):
    primary_goals: PrimaryGoalsView = Field(
        default_factory=PrimaryGoalsView,
        validation_alias=AliasChoices("primary_goals", "primaryGoals"),
        serialization_alias="primaryGoals",
    )
    study_availability: StudyAvailabilityView = Field(
        default_factory=StudyAvailabilityView,
        validation_alias=AliasChoices("study_availability", "studyAvailability"),
        serialization_alias="studyAvailability",
    )
    profiling: ProfilingView = Field(default_factory=ProfilingView)
    notifications: NotificationView = Field(default_factory=NotificationView)
