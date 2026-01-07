from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, model_validator


class CoachingTipCreateRequest(BaseModel):
    session_id: str = Field(
        ...,
        validation_alias=AliasChoices("session_id", "sessionId"),
        serialization_alias="sessionId",
    )
    model_config = {"populate_by_name": True}


class CoachingTipCreate(BaseModel):
    session_id: str = Field(serialization_alias="sessionId")
    user_id: str = Field(serialization_alias="userId")
    tip_text: str = Field(serialization_alias="tipText")
    practice_words: Optional[List[str]] = Field(default=None, serialization_alias="practiceWords")
    provider_meta: Dict[str, Any] = Field(default_factory=dict, serialization_alias="providerMeta")
    feedback: Dict[str, Any] = Field(default_factory=dict, serialization_alias="feedback")
    prompt_version: str = Field(default="v1", serialization_alias="promptVersion")
    created_at: int = Field(default_factory=lambda: int(time.time()), serialization_alias="createdAt")

    model_config = {"populate_by_name": True}


class CoachingTipResponse(BaseModel):
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    session_id: str = Field(
        ...,
        validation_alias=AliasChoices("session_id", "sessionId"),
        serialization_alias="sessionId",
    )
    user_id: str = Field(
        ...,
        validation_alias=AliasChoices("user_id", "userId"),
        serialization_alias="userId",
    )
    created_at: int = Field(
        ...,
        validation_alias=AliasChoices("created_at", "createdAt"),
        serialization_alias="createdAt",
    )
    tip_text: str = Field(serialization_alias="tipText")
    practice_words: Optional[List[str]] = Field(default=None, serialization_alias="practiceWords")
    provider_meta: Dict[str, Any] = Field(default_factory=dict, serialization_alias="providerMeta")
    feedback: Dict[str, Any] = Field(default_factory=dict, serialization_alias="feedback")
    prompt_version: str = Field(default="v1", serialization_alias="promptVersion")

    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if values is None:
            return values
        if "_id" in values and isinstance(values["_id"], ObjectId):
            oid_str = str(values["_id"])
            values["id"] = values.get("id") or oid_str
            values["_id"] = oid_str
        elif "_id" in values and values.get("id") is None:
            try:
                values["id"] = str(values["_id"])
            except Exception:
                pass
        return values

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class CoachingTipListItem(BaseModel):
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    session_id: str = Field(
        ...,
        validation_alias=AliasChoices("session_id", "sessionId"),
        serialization_alias="sessionId",
    )
    created_at: int = Field(
        ...,
        validation_alias=AliasChoices("created_at", "createdAt"),
        serialization_alias="createdAt",
    )
    preview: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if values is None:
            return values
        if "_id" in values and isinstance(values["_id"], ObjectId):
            oid_str = str(values["_id"])
            values["id"] = values.get("id") or oid_str
            values["_id"] = oid_str
        elif "_id" in values and values.get("id") is None:
            try:
                values["id"] = str(values["_id"])
            except Exception:
                pass
        return values

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class CoachingTipListResponse(BaseModel):
    items: List[CoachingTipListItem]
