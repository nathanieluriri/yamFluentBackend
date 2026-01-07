# ============================================================================
# SETTINGS SERVICE
# ============================================================================
# This file was auto-generated on: 2026-01-07 10:53:39 WAT
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

from bson import ObjectId
from fastapi import HTTPException
from typing import List

from repositories.settings import (
    create_settings,
    get_settings,
    get_settingss,
    update_settings,
    delete_settings,
)
from schemas.settings import SettingsCreate, SettingsUpdate, SettingsOut


async def add_settings(settings_data: SettingsCreate) -> SettingsOut:
    """adds an entry of SettingsCreate to the database and returns an object

    Returns:
        _type_: SettingsOut
    """
    return await create_settings(settings_data)


async def remove_settings(settings_id: str):
    """deletes a field from the database and removes SettingsCreateobject 

    Raises:
        HTTPException 400: Invalid settings ID format
        HTTPException 404:  Settings not found
    """
    if not ObjectId.is_valid(settings_id):
        raise HTTPException(status_code=400, detail="Invalid settings ID format")

    filter_dict = {"_id": ObjectId(settings_id)}
    result = await delete_settings(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Settings not found")

    else: return True
    
async def retrieve_settings_by_settings_id(id: str) -> SettingsOut:
    """Retrieves settings object based specific Id 

    Raises:
        HTTPException 404(not found): if  Settings not found in the db
        HTTPException 400(bad request): if  Invalid settings ID format

    Returns:
        _type_: SettingsOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid settings ID format")

    filter_dict = {"_id": ObjectId(id)}
    result = await get_settings(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="Settings not found")

    return result


async def retrieve_settingss(start=0,stop=100) -> List[SettingsOut]:
    """Retrieves SettingsOut Objects in a list

    Returns:
        _type_: SettingsOut
    """
    return await get_settingss(start=start,stop=stop)


async def update_settings_by_id(settings_id: str, settings_data: SettingsUpdate) -> SettingsOut:
    """updates an entry of settings in the database

    Raises:
        HTTPException 404(not found): if Settings not found or update failed
        HTTPException 400(not found): Invalid settings ID format

    Returns:
        _type_: SettingsOut
    """
    if not ObjectId.is_valid(settings_id):
        raise HTTPException(status_code=400, detail="Invalid settings ID format")

    filter_dict = {"_id": ObjectId(settings_id)}
    result = await update_settings(filter_dict, settings_data)

    if not result:
        raise HTTPException(status_code=404, detail="Settings not found or update failed")

    return result