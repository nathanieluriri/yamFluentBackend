
from fastapi import APIRouter, HTTPException, Query, status, Path, Request, Depends, Body
from typing import List,Annotated, Optional
from schemas.imports import ScenarioName
from schemas.response_schema import APIResponse
from schemas.session import SessionOut
from schemas.tokens_schema import accessTokenOut
from schemas.admin_schema import (
    AdminCreate,
    AdminOut,
    AdminBase,
    AdminUpdate,
    AdminRefresh,
    AdminLogin
)
from core.admin_logger import log_what_admin_does
from security.account_status_check import check_admin_account_status_and_permissions
from services.admin_service import (
    add_admin,
    remove_admin,
    retrieve_admins,
    authenticate_admin,
    retrieve_admin_by_admin_id,
    update_admin,
    logout_admin as logout_admin_service,
    refresh_admin_tokens_reduce_number_of_logins,

)
from services.email_service import send_invite_notification
from security.auth import verify_token_to_refresh,verify_admin_token
from services.session_service import remove_session, retrieve_sessions
router = APIRouter(prefix="/admins", tags=["Admins"])


def _base_url_from_request(request: Request) -> str:
    base_url = str(request.url_for("read_root")).rstrip("/")
    return base_url.replace("http://", "https://", 1)


def _absolute_audio_urls(sessions: List[SessionOut], base_url: str) -> List[SessionOut]:
    updated = []
    for session in sessions:
        copy = session.model_copy(deep=True)
        script = getattr(copy, "script", None)
        turns = getattr(script, "turns", None) if script else None
        if turns:
            for turn in turns:
                model_audio_url = getattr(turn, "model_audio_url", None)
                if isinstance(model_audio_url, str) and model_audio_url.startswith("/"):
                    turn.model_audio_url = f"{base_url}{model_audio_url}"
                user_audio_url = getattr(turn, "user_audio_url", None)
                if isinstance(user_audio_url, str) and user_audio_url.startswith("/"):
                    turn.user_audio_url = f"{base_url}{user_audio_url}"
        updated.append(copy)
    return updated
            
 

 
@router.get(
    "/", 
    response_model=APIResponse[List[AdminOut]],
    response_model_exclude_none=True,
    response_model_exclude={"data": {"__all__": {"password"}}},
    dependencies=[Depends(verify_admin_token),Depends(log_what_admin_does),Depends(check_admin_account_status_and_permissions)]
)
async def list_admins(
    
    # Use Path and Query for explicit documentation/validation of GET parameters
    start: Annotated[
        int,
        Query(ge=0, description="The starting index (offset) for the list of admins.")
    ] , 
    stop: Annotated[
        int, 
        Query(gt=0, description="The ending index for the list of admins (limit).")
    ]
):
    """
    **ADMIN ONLY:** Retrieves a paginated list of all registered admins.

    **Authorization:** Requires a **valid Access Token** (Admin role) in the 
    `Authorization: Bearer <token>` header.

    ### Examples (Illustrative URLs):

    * **First Page:** `/admins/0/5` (Start at index 0, retrieve up to 5 admins)
    * **Second Page:** `/admins/5/10` (Start at index 5, retrieve up to 5 more admins)
    
    """
    
    # Note: The code below overrides the path parameters with hardcoded defaults (0, 100).
    # You should typically use the passed parameters: 
    # items = await retrieve_admins(start=start, stop=stop)
    
    # Using the hardcoded values from your original code:
    items = await retrieve_admins(start=0, stop=100)
    
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.get(
    "/profile", 
    response_model=APIResponse[AdminOut],
    dependencies=[Depends(verify_admin_token),Depends(log_what_admin_does),Depends(check_admin_account_status_and_permissions)],
    response_model_exclude_none=True,
    response_model_exclude={"data": {"password"}},
)
async def get_my_admin(
    token: accessTokenOut = Depends(verify_admin_token),
        
):
    """
    Retrieves the profile information for the currently authenticated admin.

    The admin's ID is automatically extracted from the valid Access Token 
    in the **Authorization: Bearer <token>** header.
    """
    
    items = await retrieve_admin_by_admin_id(id=token.get("userId"))
    return APIResponse(status_code=200, data=items, detail="admins items fetched")





@router.post("/signup",dependencies=[Depends(verify_admin_token),Depends(log_what_admin_does),Depends(check_admin_account_status_and_permissions)],response_model_exclude_none=True, response_model_exclude={"data": {"password"}},response_model=APIResponse[AdminOut])
async def signup_new_admin(
    admin_data:AdminBase,
    token: accessTokenOut = Depends(verify_admin_token),
):
 
    admin_data_dict = admin_data.model_dump() 
    new_admin = AdminCreate(
      invited_by=token.get("userId"),
        **admin_data_dict
    )
    items = await add_admin(admin_data=new_admin,password=admin_data_dict['password'])
    
    
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")

@router.post("/login",response_model_exclude={"data": {"password"}}, response_model_exclude_none=True,response_model=APIResponse[AdminOut])
async def login_admin(
    
    admin_data:AdminLogin,

):
    """
    Authenticates a admin with the provided email and password.
    
    Upon success, returns the authenticated admin data and an authentication token.
    """
    items = await authenticate_admin(admin_data=admin_data)
    # The `authenticate_admin` function should raise an HTTPException 
    # (e.g., 401 Unauthorized) on failure.
    
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")



@router.post(
    "/refresh",
    response_model=APIResponse[AdminOut],
    dependencies=[Depends(verify_token_to_refresh)],
    response_model_exclude={"data": {"password"}},
)
async def refresh_admin_tokens(
    admin_data: Annotated[
        AdminRefresh,
        Body(
            openapi_examples={
                "successful_refresh": {
                    "summary": "Successful Token Refresh",
                    "description": (
                        "The correct payload for refreshing tokens. "
                        "The **expired access token** is provided in the `Authorization: Bearer <token>` header."
                    ),
                    "value": {
                        # A long-lived, valid refresh token
                        "refresh_token": "valid.long.lived.refresh.token.98765"
                    },
                },
                "invalid_refresh_token": {
                    "summary": "Invalid Refresh Token",
                    "description": (
                        "Payload that would fail the refresh process because the **refresh_token** "
                        "in the body is invalid or has expired."
                    ),
                    "value": {
                        "refresh_token": "expired.or.malformed.refresh.token.00000"
                    },
                },
                "mismatched_tokens": {
                    "summary": "Tokens Belong to Different Admins",
                    "description": (
                        "A critical security failure example: the refresh token in the body "
                        "does not match the admin ID associated with the expired access token in the header. "
                        "This should result in a **401 Unauthorized**."
                    ),
                    "value": {
                        "refresh_token": "refresh.token.of.different.admin.77777"
                    },
                },
            }
        ),
    ],
    token: accessTokenOut = Depends(verify_token_to_refresh)
):
    """
    Refreshes the admin's access token and returns a new token pair.

    Requires an **expired access token** in the Authorization header and a **valid refresh token** in the body.
    """
 
    items = await refresh_admin_tokens_reduce_number_of_logins(
        admin_refresh_data=admin_data,
        expired_access_token=token.accesstoken
    )
    
    # Clears the password before returning, which is good practice.
    items.password = ''
    
    return APIResponse(status_code=200, data=items, detail="admins items fetched")




@router.post(
    "/logout",
    dependencies=[
        Depends(verify_admin_token),
        Depends(log_what_admin_does),
        Depends(check_admin_account_status_and_permissions),
    ],
    response_model=APIResponse[None],
)
async def logout_admin(
    token: accessTokenOut = Depends(verify_admin_token),
):
    """
    Logs out the currently authenticated admin.

    This action invalidates the admin’s active session(s) by
    revoking refresh tokens and/or marking tokens as unusable.

    **Authorization:**  
    Requires a valid Access Token in the  
    `Authorization: Bearer <token>` header.
    """

    await logout_admin_service(admin_id=token.get("userId"))

    return APIResponse(
        status_code=status.HTTP_200_OK,
        data=None,
        detail="Logged out successfully",
    )


@router.delete("/account",dependencies=[Depends(verify_admin_token),Depends(log_what_admin_does)], response_model_exclude_none=True)
async def delete_admin_account(
    token: accessTokenOut = Depends(verify_admin_token),
 
):
    """
    Deletes the account associated with the provided access token.

    The admin ID is extracted from the valid Access Token in the Authorization header.
    No request body is required.
    """
    result = await remove_admin(admin_id=token.userId)
    
    # The 'result' is assumed to be a standard FastAPI response object or a dict/model 
    # that is automatically converted to a response.
    return result






# ------------------------------
# Delete an existing Session
# ------------------------------

@router.delete("/{user_id}/{id}", response_model=APIResponse[None])
async def delete_session(id: str = Path(..., description="ID of the session to delete"),user_id:str = Path(..., description="User Id of the session to delete") ,token:accessTokenOut = Depends(verify_admin_token)):
    """
    Deletes an existing Session by its ID.
    """
    deleted = await remove_session(id,user_id=user_id)
    if not deleted:
        # This assumes remove_session returns a boolean or similar
        # to indicate if deletion was successful (i.e., item was found).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found or deletion failed")
    
    return APIResponse(status_code=200, data=None, detail=f"Session deleted successfully")





# ------------------------------
# List Sessions (with pagination and filtering)
# ------------------------------
@router.get("/", response_model=APIResponse[List[SessionOut]],dependencies=[Depends(verify_admin_token)],)
async def list_sessions(
    request: Request,
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for page-based pagination (0-indexed)"),
    
    # New: Filter parameter expects a JSON string
    filters: Optional[ScenarioName] = Query(None, description="Optional Scenario name string "),
    user_id:str = Path(..., description="User Id of the user you want to view their session"),

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
        items = await retrieve_sessions(filters=parsed_filters, start=start, stop=stop,user_id=user_id)
        base_url = _base_url_from_request(request)
        items = _absolute_audio_urls(items, base_url)
        return APIResponse(status_code=200, data=items, detail="Fetched successfully")

    # Case 2: Use page_number if provided
    elif page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative.")
        
        start_index = page_number * PAGE_SIZE
        stop_index = start_index + PAGE_SIZE
        # Pass filters to the service layer
        items = await retrieve_sessions(filters=parsed_filters, start=start_index, stop=stop_index,user_id=user_id)
        base_url = _base_url_from_request(request)
        items = _absolute_audio_urls(items, base_url)
        return APIResponse(status_code=200, data=items, detail=f"Fetched page {page_number} successfully")

    # Case 3: Default (no params)
    else:
        # Pass filters to the service layer
        items = await retrieve_sessions(filters=parsed_filters, start=0, stop=100,user_id=user_id)
        base_url = _base_url_from_request(request)
        items = _absolute_audio_urls(items, base_url)
        detail_msg = "Fetched first 100 records successfully"
        if parsed_filters:
            # If filters were applied, adjust the detail message
            detail_msg = f"Fetched first 100 records successfully (with filters applied)"
        return APIResponse(status_code=200, data=items, detail=detail_msg)

