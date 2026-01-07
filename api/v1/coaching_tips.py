from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from schemas.coaching_tips import (
    CoachingTipCreateRequest,
    CoachingTipListItem,
    CoachingTipResponse,
)
from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from security.auth import verify_token_user_role
from services.coaching_tips_service import (
    generate_or_get_coaching_tip,
    get_user_coaching_tip_by_id,
    list_user_coaching_tips,
)

router = APIRouter(prefix="/coaching-tips", tags=["Coaching Tips"])


@router.post(
    "/",
    response_model=APIResponse[CoachingTipResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_coaching_tip(
    payload: CoachingTipCreateRequest,
    user: accessTokenOut = Depends(verify_token_user_role),
):
    tip = await generate_or_get_coaching_tip(create_request=payload, user=user)
    return APIResponse(status_code=201, data=tip, detail="Coaching tip ready")


@router.get(
    "/",
    response_model=APIResponse[List[CoachingTipListItem]],
)
async def list_coaching_tips(
    start: Optional[int] = Query(0, description="Start index for pagination"),
    stop: Optional[int] = Query(50, description="Stop index for pagination"),
    user: accessTokenOut = Depends(verify_token_user_role),
):
    if start is None or stop is None:
        raise HTTPException(status_code=400, detail="Start and stop must be provided")
    items = await list_user_coaching_tips(user=user, start=start, stop=stop)
    return APIResponse(status_code=200, data=items, detail="Fetched coaching tips")


@router.get(
    "/{tip_id}",
    response_model=APIResponse[CoachingTipResponse],
)
async def get_coaching_tip(
    tip_id: str = Path(..., description="Coaching tip ID"),
    user: accessTokenOut = Depends(verify_token_user_role),
):
    tip = await get_user_coaching_tip_by_id(tip_id=tip_id, user=user)
    return APIResponse(status_code=200, data=tip, detail="Fetched coaching tip")
