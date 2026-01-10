import os
import re
from datetime import datetime
from urllib.parse import quote, urlparse
from fastapi import APIRouter, Request, status, Depends, Form, HTTPException
from typing import List, Dict, Any
from fastapi.responses import RedirectResponse, JSONResponse
from schemas.imports import (
    ResetPasswordConclusion,
    ResetPasswordInitiation,
    ResetPasswordInitiationResponse,
    UserType,
    NativeLanguage,
    CurrentProficiency,
    MainGoals,
    LearnerType,
    DailyPracticeTime,
)
from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserOut,
    UserBase,
    UserScenerioOptions,
    UserSignUp,
    UserUpdateProfile,
    UserPersonalProfilingDataOptions,
    UserRefresh,
    LoginType,
    UserUpdatePassword,
    build_user_scenerio_options,
)
from services.user_service import (
    add_user,
    remove_user,
    retrieve_users,
    authenticate_user,
    retrieve_user_by_user_id,
 
    update_user_by_id,
    logout_user as logout_user_service,
   
    oauth,
    user_reset_password_conclusion,
    user_reset_password_intiation,
    get_reset_token_state,
    refresh_user_tokens_reduce_number_of_logins
)
from services.password_reset_web_service import (
    render_reset_error_response,
    render_reset_landing_response,
    render_reset_success_response,
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
            f"yamfluent://auth/callback?accessToken={access_token}&refreshToken={refresh_token}"
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



# @router.delete("/account",dependencies=[Depends(verify_token_user_role)])
# async def delete_user_account(token:accessTokenOut = Depends(verify_token_user_role)):
#     result = await remove_user(user_id=token.userId)
#     return result




# -------------------------
# -------- Onboarding -----
# -------------------------

@router.patch("/onboard/complete",response_model=APIResponse[UserOut], dependencies=[Depends(verify_token_user_role)],response_model_exclude={"data":{"password"}})
async def update_onboarding_information_and_complete_user_profile(driver_details:UserUpdateProfile,token:accessTokenOut = Depends(verify_token_user_role)):
    driver =  await update_user_by_id(driver_id=token.userId,driver_data=driver_details)
    return APIResponse(data = driver,status_code=200,detail="Successfully updated profile")
 

@router.get(
    "/onboarding/options",
    response_model=APIResponse[UserPersonalProfilingDataOptions],
    dependencies=[Depends(verify_token_user_role)],
    response_model_exclude_none=True,
)
async def retrieve_onboarding_options():
    payload = UserPersonalProfilingDataOptions(
        nativeLanguages=[language.value for language in NativeLanguage],
        currentProficiencies=[level.value for level in CurrentProficiency],
        mainGoals=[goal.value for goal in MainGoals],
        learnerTypes=[learner.value for learner in LearnerType],
        dailyPracticeTimes=[time.value for time in DailyPracticeTime],
    )
    return APIResponse(status_code=200, data=payload, detail="Fetched successfully")



# -------------------------
# -------- scenerios -----
# -------------------------
@router.get(
    "/scenerio/options",
    response_model=APIResponse[List[UserScenerioOptions]],
    dependencies=[Depends(verify_token_user_role)],
    response_model_exclude_none=True,
)
def get_scenerio_options():
    return APIResponse(data=build_user_scenerio_options(),status_code=200,detail="Fetched successfully")

 
# -----------------------------------
# ------- PASSWORD MANAGEMENT ------- 
# -----------------------------------

 
@router.patch("/password-reset",dependencies=[Depends(verify_token_user_role)])
async def update_driver_password_while_logged_in(driver_details:UserUpdatePassword,token:accessTokenOut = Depends(verify_token_user_role)):
    driver =  await update_user_by_id(driver_id=token.userId,driver_data=driver_details,is_password_getting_changed=True)
    return APIResponse(data = driver,status_code=200,detail="Successfully updated profile")


async def _validate_reset_token_for_web(reset_token: str) -> str:
    if not reset_token or len(reset_token) < 10:
        return "This reset link is invalid."

    token_state = await get_reset_token_state(reset_token)
     
    if not token_state:
        return "This reset link is invalid or expired."

    if token_state["userType"] != UserType.member.value:
        return "This reset link is invalid or expired."

    if token_state["used"]:
        return "This reset link has already been used."

    if token_state["expiresAt"] <= int(datetime.utcnow().timestamp()):
        return "This reset link has expired."

    return ""


@router.post(
    "/password-reset/request",
    response_model=APIResponse[ResetPasswordInitiationResponse],
    summary="Request password reset magic link",
    description=(
        "Starts the password reset flow by emailing a magic link. "
        "Always returns a generic success message to avoid user enumeration."
    ),
)
async def start_password_reset_process_for_driver_that_forgot_password(
    request: Request,
    driver_details: ResetPasswordInitiation
):
    """Email a magic-link reset token to the provided address if it exists."""
    
    redirect_uri = str(request.url_for("mobile_auth_callback_user"))
    redirect_uri = re.sub(r"^http://", "https://", redirect_uri)
    parsed = urlparse(redirect_uri)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    driver =  await user_reset_password_intiation(
        user_details=driver_details,
        base_url=base_url
    )
    return APIResponse(data = driver,status_code=200,detail="Successfully updated profile")


@router.get("/auth/reset-password")
async def reset_password_landing_page(reset_token: str):
    error_message = await _validate_reset_token_for_web(reset_token)
    if error_message:
        return render_reset_error_response(error_message, status_code=400)

    app_scheme = os.getenv("APP_SCHEME", "yamfluent").replace("://", "")
    deep_link = f"{app_scheme}://auth/reset-password?reset_token={reset_token}"
    return render_reset_landing_response(reset_token, deep_link)


@router.post("/auth/reset-password")
async def reset_password_from_web(
    request: Request,
    reset_token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    accept_header = request.headers.get("accept", "").lower()
    wants_json = "application/json" in accept_header

    error_message = await _validate_reset_token_for_web(reset_token)
    if error_message:
        if wants_json:
            return JSONResponse(status_code=400, content={"detail": error_message})
        return render_reset_error_response(error_message, status_code=400)

    if password != confirm_password:
        message = "Passwords do not match."
        if wants_json:
            return JSONResponse(status_code=400, content={"detail": message})
        return render_reset_error_response(message, status_code=400)

    if len(password) < 8:
        message = "Password must be at least 8 characters."
        if wants_json:
            return JSONResponse(status_code=400, content={"detail": message})
        return render_reset_error_response(message, status_code=400)

    try:
        await user_reset_password_conclusion(
            ResetPasswordConclusion(resetToken=reset_token, password=password)
        )
    except HTTPException as exc:
        message = str(exc.detail)
        if wants_json:
            return JSONResponse(status_code=exc.status_code, content={"detail": message})
        return render_reset_error_response(message, status_code=exc.status_code)

    if wants_json:
        return JSONResponse(status_code=200, content={"detail": "Password updated successfully."})
    return render_reset_success_response()



@router.patch(
    "/password-reset/confirm",
    response_model=APIResponse[bool],
    summary="Confirm password reset with magic link token",
    description=(
        "Resets the password using the magic link token. "
        "The token is single-use and expires after 15 minutes."
    ),
)
async def finish_password_reset_process_for_driver_that_forgot_password(
    driver_details: ResetPasswordConclusion
):
    """Reset the password using a valid reset token and a new password."""
    driver =  await user_reset_password_conclusion(driver_details)
    return APIResponse(data = driver,status_code=200,detail="Successfully updated profile")
