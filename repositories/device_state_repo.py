from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from core.database import db
from schemas.settings import DevicePushState, DevicePushStateView


async def upsert_device_state(
    user_id: str,
    payload: DevicePushState,
) -> DevicePushStateView:
    data = payload.model_dump(exclude_none=True)
    data["userId"] = user_id
    if data.get("last_synced_at") is None:
        data["last_synced_at"] = datetime.now(timezone.utc)

    result = await db.notification_devices.find_one_and_update(
        {"userId": user_id, "device_id": payload.device_id},
        {"$set": data},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return DevicePushStateView(**result)


async def get_device_state(
    user_id: str,
    device_id: str,
) -> Optional[DevicePushStateView]:
    result = await db.notification_devices.find_one(
        {"userId": user_id, "device_id": device_id}
    )
    if not result:
        return None
    return DevicePushStateView(**result)
