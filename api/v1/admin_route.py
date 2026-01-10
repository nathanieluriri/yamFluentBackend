
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
    start: Annotated[
        int,
        Query(ge=0, description="The starting index (offset) for the list of admins.")
    ] , 
    stop: Annotated[
        int, 
        Query(gt=0, description="The ending index for the list of admins (limit).")
    ]
):
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
    items = await authenticate_admin(admin_data=admin_data)
    
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
 
    items = await refresh_admin_tokens_reduce_number_of_logins(
        admin_refresh_data=admin_data,
        expired_access_token=token.accesstoken
    )
    
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
    result = await remove_admin(admin_id=token.userId)
    
    return result






@router.delete("/{user_id}/{id}", response_model=APIResponse[None])
async def delete_session(id: str = Path(..., description="ID of the session to delete"),user_id:str = Path(..., description="User Id of the session to delete") ,token:accessTokenOut = Depends(verify_admin_token)):
    deleted = await remove_session(id,user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found or deletion failed")
    
    return APIResponse(status_code=200, data=None, detail=f"Session deleted successfully")





@router.get("/", response_model=APIResponse[List[SessionOut]],dependencies=[Depends(verify_admin_token)],)
async def list_sessions(
    request: Request,
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for page-based pagination (0-indexed)"),
    filters: Optional[ScenarioName] = Query(None, description="Optional Scenario name string "),
    user_id:str = Path(..., description="User Id of the user you want to view their session"),

):
    PAGE_SIZE = 50
    parsed_filters = {}
    
    
    
    

    if filters:
        try:
            parsed_filters =  {"scenario":filters.value}
        except :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for 'filters' query parameter."
            )

    if start is not None or stop is not None:
        if start is None or stop is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both 'start' and 'stop' must be provided together.")
        if stop < start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'stop' cannot be less than 'start'.")
        
        items = await retrieve_sessions(filters=parsed_filters, start=start, stop=stop,user_id=user_id)
        base_url = _base_url_from_request(request)
        items = _absolute_audio_urls(items, base_url)
        return APIResponse(status_code=200, data=items, detail="Fetched successfully")

    elif page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative.")
        
        start_index = page_number * PAGE_SIZE
        stop_index = start_index + PAGE_SIZE
        items = await retrieve_sessions(filters=parsed_filters, start=start_index, stop=stop_index,user_id=user_id)
        base_url = _base_url_from_request(request)
        items = _absolute_audio_urls(items, base_url)
        return APIResponse(status_code=200, data=items, detail=f"Fetched page {page_number} successfully")

    else:
        items = await retrieve_sessions(filters=parsed_filters, start=0, stop=100,user_id=user_id)
        base_url = _base_url_from_request(request)
        items = _absolute_audio_urls(items, base_url)
        detail_msg = "Fetched first 100 records successfully"
        if parsed_filters:
            detail_msg = f"Fetched first 100 records successfully (with filters applied)"
        return APIResponse(status_code=200, data=items, detail=detail_msg)

