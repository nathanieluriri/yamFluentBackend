import re
from urllib.parse import quote
from fastapi import APIRouter, Request, status, Depends
from typing import Dict, Any
from fastapi.responses import RedirectResponse
from schemas.imports import ResetPasswordConclusion, ResetPasswordInitiation, ResetPasswordInitiationResponse
from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserOut,
    UserBase,
    UserSignUp,
  
    UserRefresh,
    LoginType,
    UserUpdatePassword,
)
from services.user_service import (
    add_user,
    remove_user,
    
    authenticate_user,
    retrieve_user_by_user_id,
 
    update_user_by_id,
    logout_user as logout_user_service,
   
    oauth,
    user_reset_password_conclusion,
    user_reset_password_intiation,
    refresh_user_tokens_reduce_number_of_logins
)
from security.auth import verify_token_to_refresh,verify_token_user_role





router = APIRouter(prefix="/users", tags=["Users"])

# --- Step 1: Redirect user to Google login ---
@router.get("/mobile/google/auth", response_model_exclude={"data": {"password","loginType","oauth_access_token","oauth_refresh_token"}})
async def mobile_login_with_google_account(request: Request)->None:
    redirect_uri = str(request.url_for("mobile_auth_callback_user"))

    # Force https
    redirect_uri = re.sub(r"^http://", "https://", redirect_uri)

    return await oauth.google.authorize_redirect(request, redirect_uri)  # type: ignore

# --- Step 2: Handle callback from Google ---

@router.get("/mobile/auth/callback", response_model_exclude={"data": {"password","loginType","oauth_access_token","oauth_refresh_token"}}, name="mobile_auth_callback_user")
async def mobile_auth_callback_user(request: Request):
    token: Dict[str, Any] = await oauth.google.authorize_access_token(request)  # type: ignore
    user_info: Dict[str, Any] = token.get("userinfo")  # type: ignore
    google_access_token: str = token.get("access_token")  # type: ignore
    google_refresh_token: str = token.get("refresh_token")  # type: ignore
    if user_info:
        user = UserBase(
            firstName=user_info["name"],
            lastName=user_info["given_name"],
            email=user_info["email"],
            password="",
            loginType=LoginType.google,
            oauth_access_token=google_access_token,
            oauth_refresh_token=google_refresh_token,
        )
        data = await authenticate_user(user_data=user)
        if data is None:
            new_user = UserCreate(**user.model_dump())
            items = await add_user(user_data=new_user)
            access_token = items.access_token
            refresh_token = items.refresh_token
        else:
            access_token = data.access_token
            refresh_token = data.refresh_token

        success_url = (
            f"yamfluent://auth/callback?access_token={access_token}&refresh_token={refresh_token}"
        )

        return RedirectResponse(
            url=success_url,
            status_code=status.HTTP_302_FOUND
        )
    message = quote("No user info found")
    error_url = f"yamfluent://auth/callback?status=400&message={message}"
    return RedirectResponse(
        url=error_url,
        status_code=status.HTTP_302_FOUND
    )

 
@router.get("/me", response_model_exclude={"data": {"password","loginType","oauth_access_token","oauth_refresh_token"}},response_model=APIResponse[UserOut],dependencies=[Depends(verify_token_user_role)],response_model_exclude_none=True)
async def get_my_users(token:accessTokenOut = Depends(verify_token_user_role)):
    items = await retrieve_user_by_user_id(id=token.userId)
    return APIResponse(status_code=200, data=items, detail="users items fetched")



@router.post("/signup", response_model_exclude={"data": {"password","loginType","oauth_access_token","oauth_refresh_token"}},response_model=APIResponse[UserOut])
async def signup_new_user(user_data:UserSignUp):
    
    new_user = UserCreate(**user_data.model_dump(),loginType=LoginType.password)
    items = await add_user(user_data=new_user)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.post("/login",response_model_exclude={"data": {"password","loginType","oauth_access_token","oauth_refresh_token"}}, response_model=APIResponse[UserOut])
async def login_user(user_data:UserLogin):
    user_base = UserBase(**user_data.model_dump(),loginType=LoginType.password)
    items = await authenticate_user(user_data=user_base)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.post("/refresh",response_model_exclude={"data": {"password"}},response_model=APIResponse[UserOut],dependencies=[Depends(verify_token_to_refresh)])
async def refresh_user_tokens(user_data:UserRefresh,token:accessTokenOut = Depends(verify_token_to_refresh)):
    
    items= await refresh_user_tokens_reduce_number_of_logins(user_refresh_data=user_data,expired_access_token=token.accesstoken)  # type: ignore

    return APIResponse(status_code=200, data=items, detail="users items fetched")


@router.post("/logout")
async def logout_user(
    token: accessTokenOut = Depends(verify_token_user_role),
):
    """
    Logs out the currently authenticated admin.

    This action invalidates the admin’s active session(s) by
    revoking refresh tokens and/or marking tokens as unusable.

    **Authorization:**  
    Requires a valid Access Token in the  
    `Authorization: Bearer <token>` header.
    """

    await logout_user_service(user_id=token.userId)

    return APIResponse(
        status_code=status.HTTP_200_OK,
        data=None,
        detail="Logged out successfully",
    )



@router.delete("/account",dependencies=[Depends(verify_token_user_role)])
async def delete_user_account(token:accessTokenOut = Depends(verify_token_user_role)):
    result = await remove_user(user_id=token.userId)
    return result




 
# -----------------------------------
# ------- PASSWORD MANAGEMENT ------- 
# -----------------------------------

 
@router.patch("/password-reset",dependencies=[Depends(verify_token_user_role)])
async def update_driver_password_while_logged_in(driver_details:UserUpdatePassword,token:accessTokenOut = Depends(verify_token_user_role)):
    driver =  await update_user_by_id(driver_id=token.userId,driver_data=driver_details,is_password_getting_changed=True)
    return APIResponse(data = driver,status_code=200,detail="Successfully updated profile")



@router.post("/password-reset/request",response_model=APIResponse[ResetPasswordInitiationResponse] )
async def start_password_reset_process_for_driver_that_forgot_password(driver_details:ResetPasswordInitiation):
    driver =  await user_reset_password_intiation(user_details=driver_details)   
    return APIResponse(data = driver,status_code=200,detail="Successfully updated profile")



@router.patch("/password-reset/confirm")
async def finish_password_reset_process_for_driver_that_forgot_password(driver_details:ResetPasswordConclusion):
    driver =  await user_reset_password_conclusion(driver_details)
    return APIResponse(data = driver,status_code=200,detail="Successfully updated profile")
