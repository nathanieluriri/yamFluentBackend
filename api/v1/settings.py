from fastapi import APIRouter, Depends, Query, status

from schemas.response_schema import APIResponse
from schemas.settings import DevicePushState, NotificationView, SettingsRequest, SettingsView
from schemas.tokens_schema import accessTokenOut
from security.auth import verify_token_user_role
from services.settings_service import (
    apply_settings_request,
    get_settings_view,
    sync_device_state,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_model=APIResponse[SettingsView])
async def get_user_settings(
    device_id: str | None = Query(
        default=None,
        description="Optional device ID to compute per-device notification status.",
    ),
    user: accessTokenOut = Depends(verify_token_user_role),
):
    item = await get_settings_view(user_id=user.userId, device_id=device_id)
    return APIResponse(status_code=200, data=item, detail="Settings fetched")


@router.patch("/", response_model=APIResponse[SettingsView])
async def update_user_settings(
    payload: SettingsRequest,
    user: accessTokenOut = Depends(verify_token_user_role),
):
    updated_item = await apply_settings_request(user_id=user.userId, payload=payload)
    if payload.account.delete_account:
        return APIResponse(
            status_code=status.HTTP_200_OK,
            data=None,
            detail="Account deleted successfully",
        )
    if payload.account.reset_account:
        return APIResponse(
            status_code=status.HTTP_200_OK,
            data=None,
            detail="Account reset successfully",
        )
    return APIResponse(
        status_code=status.HTTP_200_OK,
        data=updated_item,
        detail="Settings updated successfully",
    )


@router.post("/notifications/device-state", response_model=APIResponse[NotificationView])
async def upsert_device_state(
    payload: DevicePushState,
    user: accessTokenOut = Depends(verify_token_user_role),
):
    notification_view = await sync_device_state(user_id=user.userId, payload=payload)
    return APIResponse(
        status_code=status.HTTP_200_OK,
        data=notification_view,
        detail="Device notification state synced",
    )
