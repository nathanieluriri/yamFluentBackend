from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from core.database import db
from schemas.coaching_tips import (
    CoachingTipCreate,
    CoachingTipListItem,
    CoachingTipResponse,
)

COLLECTION_NAME = "coaching_tips"


async def ensure_coaching_tip_indexes() -> None:
    await db[COLLECTION_NAME].create_index(
        [("session_id", 1), ("user_id", 1)],
        unique=True,
        name="uniq_session_user",
    )
    await db[COLLECTION_NAME].create_index(
        [("user_id", 1), ("created_at", -1)],
        name="user_created_at_idx",
    )


async def create_coaching_tip(
    tip_data: CoachingTipCreate,
) -> CoachingTipResponse:
    tip_dict = tip_data.model_dump()
    result = await db[COLLECTION_NAME].insert_one(tip_dict)
    doc = await db[COLLECTION_NAME].find_one({"_id": result.inserted_id})
    return CoachingTipResponse(**doc)


async def get_coaching_tip_by_session(
    *, session_id: str, user_id: str
) -> Optional[CoachingTipResponse]:
    doc = await db[COLLECTION_NAME].find_one({"session_id": session_id, "user_id": user_id})
    return CoachingTipResponse(**doc) if doc else None


async def get_coaching_tip_by_id(
    *, tip_id: str, user_id: str
) -> Optional[CoachingTipResponse]:
    if not ObjectId.is_valid(tip_id):
        return None
    doc = await db[COLLECTION_NAME].find_one({"_id": ObjectId(tip_id), "user_id": user_id})
    return CoachingTipResponse(**doc) if doc else None


async def list_coaching_tips(
    *, user_id: str, start: int = 0, stop: int = 100
) -> List[CoachingTipListItem]:
    cursor = (
        db[COLLECTION_NAME]
        .find({"user_id": user_id})
        .skip(start)
        .limit(max(0, stop - start))
        .sort("created_at", -1)
    )
    items: List[CoachingTipListItem] = []
    async for doc in cursor:
        preview = None
        tip_text = doc.get("tip_text")
        if tip_text:
            preview = tip_text[:120]
        items.append(
            CoachingTipListItem(
                **doc,
                preview=preview,
            )
        )
    return items


async def update_coaching_tip_feedback(
    *, tip_id: str, user_id: str, feedback: dict
) -> Optional[CoachingTipResponse]:
    if not ObjectId.is_valid(tip_id):
        return None
    updated = await db[COLLECTION_NAME].find_one_and_update(
        {"_id": ObjectId(tip_id), "user_id": user_id},
        {"$set": {"feedback": feedback}},
        return_document=ReturnDocument.AFTER,
    )
    return CoachingTipResponse(**updated) if updated else None


__all__ = [
    "COLLECTION_NAME",
    "ensure_coaching_tip_indexes",
    "create_coaching_tip",
    "get_coaching_tip_by_session",
    "get_coaching_tip_by_id",
    "list_coaching_tips",
    "update_coaching_tip_feedback",
    "DuplicateKeyError",
]
