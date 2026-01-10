from datetime import datetime, timedelta
from pymongo import ReturnDocument
from core.database import db
from fastapi import HTTPException,status
from typing import List,Optional
from schemas.reset_token import ResetTokenUpdate, ResetTokenCreate, ResetTokenOut

async def create_reset_token(
    reset_token_data: ResetTokenCreate,
    ttl_minutes: int = 15
) -> ResetTokenOut:

    reset_token_dict = reset_token_data.model_dump()

    reset_token_dict["expires_at"] = (
        datetime.utcnow() + timedelta(minutes=ttl_minutes)
    )

    result = await db.reset_tokens.insert_one(reset_token_dict)
    created = await db.reset_tokens.find_one(filter={"_id": result.inserted_id})
    return ResetTokenOut(**created)

async def get_reset_token(filter_dict: dict) -> Optional[ResetTokenOut]:
    try:
        result = await db.reset_tokens.find_one(filter_dict)

        if result is None:
            return None

        return ResetTokenOut(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching reset_token: {str(e)}"
        )
    
async def get_reset_tokens(filter_dict: dict = {},start=0,stop=100) -> List[ResetTokenOut]:
    try:
        if filter_dict is None:
            filter_dict = {}

        cursor = (db.reset_tokens.find(filter_dict)
        .skip(start)
        .limit(stop - start)
        )
        reset_token_list = []

        async for doc in cursor:
            reset_token_list.append(ResetTokenOut(**doc))

        return reset_token_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching reset_tokens: {str(e)}"
        )
async def update_reset_token(filter_dict: dict, reset_token_data: ResetTokenUpdate) -> ResetTokenOut:
    result = await db.reset_tokens.find_one_and_update(
        filter_dict,
        {"$set": reset_token_data.model_dump(exclude_none=True)},
        return_document=ReturnDocument.AFTER
    )
    returnable_result = ResetTokenOut(**result)
    return returnable_result

async def mark_reset_token_used(filter_dict: dict) -> ResetTokenOut:
    result = await db.reset_tokens.find_one_and_update(
        filter_dict,
        {"$set": {"used": True, "used_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER
    )
    returnable_result = ResetTokenOut(**result)
    return returnable_result
