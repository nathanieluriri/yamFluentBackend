# ============================================================================
# COACHING_TIPS SERVICE
# ============================================================================
# This file was auto-generated on: 2026-01-06 22:00:53 WAT
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

from bson import ObjectId
from fastapi import HTTPException
from typing import List

from repositories.coaching_tips import (
    create_coaching_tips,
    get_coaching_tips,
    get_coaching_tipss,
    update_coaching_tips,
    delete_coaching_tips,
)
from schemas.coaching_tips import CoachingTipsCreate, CoachingTipsUpdate, CoachingTipsOut


async def add_coaching_tips(coaching_tips_data: CoachingTipsCreate) -> CoachingTipsOut:
    """adds an entry of CoachingTipsCreate to the database and returns an object

    Returns:
        _type_: CoachingTipsOut
    """
    return await create_coaching_tips(coaching_tips_data)


async def remove_coaching_tips(coaching_tips_id: str):
    """deletes a field from the database and removes CoachingTipsCreateobject 

    Raises:
        HTTPException 400: Invalid coaching_tips ID format
        HTTPException 404:  CoachingTips not found
    """
    if not ObjectId.is_valid(coaching_tips_id):
        raise HTTPException(status_code=400, detail="Invalid coaching_tips ID format")

    filter_dict = {"_id": ObjectId(coaching_tips_id)}
    result = await delete_coaching_tips(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="CoachingTips not found")

    else: return True
    
async def retrieve_coaching_tips_by_coaching_tips_id(id: str) -> CoachingTipsOut:
    """Retrieves coaching_tips object based specific Id 

    Raises:
        HTTPException 404(not found): if  CoachingTips not found in the db
        HTTPException 400(bad request): if  Invalid coaching_tips ID format

    Returns:
        _type_: CoachingTipsOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid coaching_tips ID format")

    filter_dict = {"_id": ObjectId(id)}
    result = await get_coaching_tips(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="CoachingTips not found")

    return result


async def retrieve_coaching_tipss(start=0,stop=100) -> List[CoachingTipsOut]:
    """Retrieves CoachingTipsOut Objects in a list

    Returns:
        _type_: CoachingTipsOut
    """
    return await get_coaching_tipss(start=start,stop=stop)


async def update_coaching_tips_by_id(coaching_tips_id: str, coaching_tips_data: CoachingTipsUpdate) -> CoachingTipsOut:
    """updates an entry of coaching_tips in the database

    Raises:
        HTTPException 404(not found): if CoachingTips not found or update failed
        HTTPException 400(not found): Invalid coaching_tips ID format

    Returns:
        _type_: CoachingTipsOut
    """
    if not ObjectId.is_valid(coaching_tips_id):
        raise HTTPException(status_code=400, detail="Invalid coaching_tips ID format")

    filter_dict = {"_id": ObjectId(coaching_tips_id)}
    result = await update_coaching_tips(filter_dict, coaching_tips_data)

    if not result:
        raise HTTPException(status_code=404, detail="CoachingTips not found or update failed")

    return result