
import asyncio
import io
import logging
import os
import random
import time
from fastapi import APIRouter, Depends, File, HTTPException, Query, Path, UploadFile, status
from typing import List, Optional, Tuple
import json
from openai import (
    APIError,
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from schemas.imports import ScenarioName
from schemas.response_schema import APIResponse
from schemas.session import (
    SessionBaseRequest,
    SessionCreate,
    SessionOut,
    SessionBase,
    SessionUpdate,
    ListOfSessionOut,
)
from schemas.tokens_schema import accessTokenOut
from security.auth import verify_admin_token, verify_token_user_role
from services.session_service import (
    add_session,
    remove_session,
    retrieve_sessions,
    retrieve_session_summaries,
    retrieve_session_by_session_id,
    update_session_by_id,
)
from controller.script_generation.clients import get_openai_client

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ------------------------------
# List Sessions (with pagination and filtering)
# ------------------------------
@router.get("/", response_model=APIResponse[List[ListOfSessionOut]],dependencies=[Depends(verify_token_user_role)],)
async def list_sessions(
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for page-based pagination (0-indexed)"),
    
    # New: Filter parameter expects a JSON string
    filters: Optional[ScenarioName] = Query(None, description="Optional Scenario name string "),
    token:accessTokenOut = Depends(verify_token_user_role)
):
    """
    Retrieves a list of Sessions with pagination and optional filtering.
    - Priority 1: Range-based (start/stop)
    - Priority 2: Page-based (page_number)
    - Priority 3: Default (first 100)
    """
    PAGE_SIZE = 50
    parsed_filters = {}
    
    
    
    

    # 1. Handle Filters
    if filters:
        try:
            parsed_filters =  {"scenario":filters.value}
        except :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for 'filters' query parameter."
            )

    # 2. Determine Pagination
    # Case 1: Prefer start/stop if provided
    if start is not None or stop is not None:
        if start is None or stop is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both 'start' and 'stop' must be provided together.")
        if stop < start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'stop' cannot be less than 'start'.")
        
        # Pass filters to the service layer
        items = await retrieve_session_summaries(filters=parsed_filters, start=start, stop=stop,user_id=token.userId)
        return APIResponse(status_code=200, data=items, detail="Fetched successfully")

    # Case 2: Use page_number if provided
    elif page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative.")
        
        start_index = page_number * PAGE_SIZE
        stop_index = start_index + PAGE_SIZE
        # Pass filters to the service layer
        items = await retrieve_session_summaries(filters=parsed_filters, start=start_index, stop=stop_index,user_id=token.userId)
        return APIResponse(status_code=200, data=items, detail=f"Fetched page {page_number} successfully")

    # Case 3: Default (no params)
    else:
        # Pass filters to the service layer
        items = await retrieve_session_summaries(filters=parsed_filters, start=0, stop=100,user_id=token.userId)
        detail_msg = "Fetched first 100 records successfully"
        if parsed_filters:
            # If filters were applied, adjust the detail message
            detail_msg = f"Fetched first 100 records successfully (with filters applied)"
        return APIResponse(status_code=200, data=items, detail=detail_msg)


# ------------------------------
# Retrieve a single Session
# ------------------------------
@router.get("/{id}",dependencies=[Depends(verify_token_user_role)], response_model=APIResponse[SessionOut])
async def get_session_by_id(
    id: str = Path(..., description="session ID to fetch specific item"),
     token:accessTokenOut = Depends(verify_token_user_role)
):
    """
    Retrieves a single Session by its ID.
    """
    item = await retrieve_session_by_session_id(id=id,user_id=token.userId)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found")
    return APIResponse(status_code=200, data=item, detail="session item fetched")


# ------------------------------
# Create a new Session
# ------------------------------
# Uses SessionBase for input (correctly)
@router.post("/", dependencies=[Depends(verify_token_user_role)], response_model=APIResponse[SessionOut], status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionBaseRequest,token:accessTokenOut = Depends(verify_token_user_role)):
    """
    Creates a new Session.
    """
    # Creates SessionCreate object which includes date_created/last_updated
    new_data = SessionBase(**payload.model_dump(),userId=token.userId) 
    new_item = await add_session(new_data)
    if not new_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create session")
    
    return APIResponse(status_code=201, data=new_item, detail=f"Session created successfully")


# ------------------------------
# Update an existing Session
# ------------------------------
# Uses PATCH for partial update (correctly)
@router.patch("/{id}/{turn_index}", response_model=APIResponse[SessionOut])
async def users_turn_to_speak(
    turn_index:int,
    id: str = Path(..., description="ID of the {db_name} to update"),
    audio: UploadFile = File(..., description="User audio MP3"),
    token:accessTokenOut = Depends(verify_token_user_role)
):
    """
    Updates an existing Session by its ID.
    Assumes the service layer handles partial updates (e.g., ignores None fields in payload).
    """
     
    if audio.content_type not in ("audio/mpeg", "audio/mp3"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Audio must be an MP3 (audio/mpeg)."
        )
         
    updated_item = await update_session_by_id(session_id=id,user_id=token.userId,turn_index=turn_index,audio=audio  )
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found or update failed")
    
    return APIResponse(status_code=200, data=updated_item, detail=f"Session updated successfully")



@router.get("/openai/info", dependencies=[Depends(verify_token_user_role)])
async def openai_config_info(token: accessTokenOut = Depends(verify_token_user_role)):
    """
    Returns OpenAI org/project configuration as seen from environment variables.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    payload = {
        "openai_org_id": os.getenv("OPENAI_ORG_ID"),
        "openai_project_id": os.getenv("OPENAI_PROJECT_ID"),
        "openai_api_key_present": bool(api_key),
        "openai_api_key_prefix": f"{api_key[:6]}..." if api_key else None,
    }
    return APIResponse(status_code=200, data=payload, detail="OpenAI config info")

