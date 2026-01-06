
from fastapi import APIRouter, HTTPException, Query, Path, status
from typing import List, Optional
import json
from schemas.response_schema import APIResponse
from schemas.coaching_tips import (
    CoachingTipsCreate,
    CoachingTipsOut,
    CoachingTipsBase,
    CoachingTipsUpdate,
)
from services.coaching_tips_service import (
    add_coaching_tips,
    remove_coaching_tips,
    retrieve_coaching_tipss,
    retrieve_coaching_tips_by_coaching_tips_id,
    update_coaching_tips_by_id,
)

router = APIRouter(prefix="/coaching_tipss", tags=["CoachingTipss"])


# ------------------------------
# List CoachingTipss (with pagination and filtering)
# ------------------------------
@router.get("/", response_model=APIResponse[List[CoachingTipsOut]])
async def list_coaching_tipss(
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for page-based pagination (0-indexed)"),
    # New: Filter parameter expects a JSON string
    filters: Optional[str] = Query(None, description="Optional JSON string of MongoDB filter criteria (e.g., '{\"field\": \"value\"}')")
):
    """
    Retrieves a list of CoachingTipss with pagination and optional filtering.
    - Priority 1: Range-based (start/stop)
    - Priority 2: Page-based (page_number)
    - Priority 3: Default (first 100)
    """
    PAGE_SIZE = 50
    parsed_filters = {}

    # 1. Handle Filters
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
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
        items = await retrieve_coaching_tipss(filters=parsed_filters, start=start, stop=stop)
        return APIResponse(status_code=200, data=items, detail="Fetched successfully")

    # Case 2: Use page_number if provided
    elif page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative.")
        
        start_index = page_number * PAGE_SIZE
        stop_index = start_index + PAGE_SIZE
        # Pass filters to the service layer
        items = await retrieve_coaching_tipss(filters=parsed_filters, start=start_index, stop=stop_index)
        return APIResponse(status_code=200, data=items, detail=f"Fetched page {page_number} successfully")

    # Case 3: Default (no params)
    else:
        # Pass filters to the service layer
        items = await retrieve_coaching_tipss(filters=parsed_filters, start=0, stop=100)
        detail_msg = "Fetched first 100 records successfully"
        if parsed_filters:
            # If filters were applied, adjust the detail message
            detail_msg = f"Fetched first 100 records successfully (with filters applied)"
        return APIResponse(status_code=200, data=items, detail=detail_msg)


# ------------------------------
# Retrieve a single CoachingTips
# ------------------------------
@router.get("/{id}", response_model=APIResponse[CoachingTipsOut])
async def get_coaching_tips_by_id(
    id: str = Path(..., description="coaching_tips ID to fetch specific item")
):
    """
    Retrieves a single CoachingTips by its ID.
    """
    item = await retrieve_coaching_tips_by_coaching_tips_id(id=id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"CoachingTips not found")
    return APIResponse(status_code=200, data=item, detail="coaching_tips item fetched")


# ------------------------------
# Create a new CoachingTips
# ------------------------------
# Uses CoachingTipsBase for input (correctly)
@router.post("/", response_model=APIResponse[CoachingTipsOut], status_code=status.HTTP_201_CREATED)
async def create_coaching_tips(payload: CoachingTipsBase):
    """
    Creates a new CoachingTips.
    """
    # Creates CoachingTipsCreate object which includes date_created/last_updated
    new_data = CoachingTipsCreate(**payload.model_dump()) 
    new_item = await add_coaching_tips(new_data)
    if not new_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create coaching_tips")
    
    return APIResponse(status_code=201, data=new_item, detail=f"CoachingTips created successfully")


# ------------------------------
# Update an existing CoachingTips
# ------------------------------
# Uses PATCH for partial update (correctly)
@router.patch("/{id}", response_model=APIResponse[CoachingTipsOut])
async def update_coaching_tips(
    id: str = Path(..., description="ID of the {db_name} to update"),
    payload: CoachingTipsUpdate = None
):
    """
    Updates an existing CoachingTips by its ID.
    Assumes the service layer handles partial updates (e.g., ignores None fields in payload).
    """
    updated_item = await update_coaching_tips_by_id(id=id, data=payload)
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"CoachingTips not found or update failed")
    
    return APIResponse(status_code=200, data=updated_item, detail=f"CoachingTips updated successfully")


# ------------------------------
# Delete an existing CoachingTips
# ------------------------------
@router.delete("/{id}", response_model=APIResponse[None])
async def delete_coaching_tips(id: str = Path(..., description="ID of the coaching_tips to delete")):
    """
    Deletes an existing CoachingTips by its ID.
    """
    deleted = await remove_coaching_tips(id)
    if not deleted:
        # This assumes remove_coaching_tips returns a boolean or similar
        # to indicate if deletion was successful (i.e., item was found).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"CoachingTips not found or deletion failed")
    
    return APIResponse(status_code=200, data=None, detail=f"CoachingTips deleted successfully")
