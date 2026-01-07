from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import AliasChoices, BaseModel, Field, model_validator


class CoachingTipCreateRequest(BaseModel):
    session_id: str = Field(
        ...,
        validation_alias=AliasChoices("session_id", "sessionId"),
        serialization_alias="session_id",
    )


class CoachingTipCreate(BaseModel):
    session_id: str
    user_id: str
    tip_text: str
    practice_words: Optional[List[str]] = None
    provider_meta: Dict[str, Any] = Field(default_factory=dict)
    feedback: Dict[str, Any] = Field(default_factory=dict)
    prompt_version: str = "v1"
    created_at: int = Field(default_factory=lambda: int(time.time()))


class CoachingTipResponse(BaseModel):
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    session_id: str = Field(
        ...,
        validation_alias=AliasChoices("session_id", "sessionId"),
        serialization_alias="session_id",
    )
    user_id: str = Field(
        ...,
        validation_alias=AliasChoices("user_id", "userId"),
        serialization_alias="user_id",
    )
    created_at: int = Field(
        ...,
        validation_alias=AliasChoices("created_at", "createdAt"),
        serialization_alias="created_at",
    )
    tip_text: str
    practice_words: Optional[List[str]] = None
    provider_meta: Dict[str, Any] = Field(default_factory=dict)
    feedback: Dict[str, Any] = Field(default_factory=dict)
    prompt_version: str = "v1"

    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if values is None:
            return values
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["id"] = str(values["_id"])
        elif "_id" in values and values.get("id") is None:
            values["id"] = str(values["_id"])
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
        serialization_alias="session_id",
    )
    created_at: int = Field(
        ...,
        validation_alias=AliasChoices("created_at", "createdAt"),
        serialization_alias="created_at",
    )
    preview: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if values is None:
            return values
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["id"] = str(values["_id"])
        elif "_id" in values and values.get("id") is None:
            values["id"] = str(values["_id"])
        return values

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class CoachingTipListResponse(BaseModel):
    items: List[CoachingTipListItem]
