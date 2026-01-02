
import asyncio
import re
import secrets
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from typing import List, Optional
from repositories.reset_token import create_reset_token, get_reset_token, mark_reset_token_used
from repositories.user_repo import (
    create_user,
    get_user,
    get_users,
    update_user,
    delete_user,
)
from schemas.imports import AccountStatus, LoginType, ResetPasswordConclusion, ResetPasswordInitiation, ResetPasswordInitiationResponse, UserType
from schemas.reset_token import ResetTokenBase, ResetTokenCreate
from schemas.user_schema import UserCreate, UserUpdate, UserOut,UserBase,UserRefresh, UserUpdatePassword
from security.hash import check_password
from security.encrypting_jwt import create_jwt_member_token, create_jwt_token
from repositories.tokens_repo import add_refresh_tokens, add_access_tokens, accessTokenCreate,accessTokenOut,refreshTokenCreate
from repositories.tokens_repo import get_refresh_tokens,get_access_tokens,delete_access_token,delete_refresh_token,delete_all_tokens_with_user_id
from authlib.integrations.starlette_client import OAuth
import os
from dotenv import load_dotenv
import httpx

from services.email_service import send_password_reset_link
from core.redis_cache import cache_get_json, cache_set_json


load_dotenv()

 
oauth = OAuth()  # type: ignore
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)


async def revoke_google_token(token: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )



async def add_user(user_data: UserCreate) -> UserOut:
    """adds an entry of RiderCreate to the database and returns an object

    Returns:
        _type_: RiderOut
    """
    user =  await get_user(filter_dict={"email":user_data.email.lower()})
    if user_data.loginType==LoginType.google and user==None:
        new_rider= await create_user(user_data)
        access_token = await add_access_tokens(token_data=accessTokenCreate(userId=new_rider.id))
        refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=new_rider.id,previousAccessToken=access_token.accesstoken))
        token_activation = True
        token = create_jwt_token(access_token=access_token.accesstoken,user_id=new_rider.id,user_type="USER",is_activated=token_activation) 
        new_rider.refresh_token = refresh_token.refreshtoken
        new_rider.access_token= token
        return new_rider
    if user_data.loginType==LoginType.password and user==None:
        new_rider= await create_user(user_data)
        if new_rider==None:
            raise HTTPException(status_code=500,detail="Error In Creation of user ")
        access_token = await add_access_tokens(token_data=accessTokenCreate(userId=new_rider.id))
        refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=new_rider.id,previousAccessToken=access_token.accesstoken))
        new_rider.password=""
        token_activation = True
        token = create_jwt_token(access_token=access_token.accesstoken,user_id=new_rider.id,user_type="USER",is_activated=token_activation) 
        new_rider.refresh_token = refresh_token.refreshtoken
        new_rider.access_token= token
        return new_rider
    else:
        raise HTTPException(status_code=409,detail="User Already exists")
async def authenticate_user(user_data:UserBase )->Optional[UserOut]:
    user = await get_user(filter_dict={"email":user_data.email.lower()})
    if user_data.loginType==LoginType.google and user != None:
        user.password=""
        access_token = await add_access_tokens(token_data=accessTokenCreate(userId=user.id))
        refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=user.id,previousAccessToken=access_token.accesstoken))
        active = user.accountStatus==AccountStatus.ACTIVE
        token = create_jwt_token(access_token=access_token.accesstoken,user_id=user.id,user_type="USER",is_activated=active)            
        user.access_token= token
        user.refresh_token = refresh_token.refreshtoken
        return user
    if user_data.loginType==LoginType.google and user == None:
        
        return None
    elif user_data.loginType==LoginType.password and user != None:
        if check_password(password=user_data.password,hashed=user.password ):
            user.password=""
            access_token = await add_access_tokens(token_data=accessTokenCreate(userId=user.id))
            refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=user.id,previousAccessToken=access_token.accesstoken))
            active = user.accountStatus==AccountStatus.ACTIVE
            token = create_jwt_token(access_token=access_token.accesstoken,user_id=user.id,user_type="USER",is_activated=active)            
            user.access_token= token
            user.refresh_token = refresh_token.refreshtoken
            return user
        else:
            raise HTTPException(status_code=401, detail="Unathorized, Invalid Login credentials")
    else:
        raise HTTPException(status_code=404,detail="USER not found")

async def refresh_user_tokens_reduce_number_of_logins(user_refresh_data:UserRefresh,expired_access_token):
    refreshObj= await get_refresh_tokens(user_refresh_data.refresh_token)
    if refreshObj:
        if refreshObj.previousAccessToken==expired_access_token:
            user = await get_user(filter_dict={"_id":ObjectId(refreshObj.userId)})
            
            if user!= None:
                    access_token = await add_access_tokens(token_data=accessTokenCreate(userId=user.id))
                    refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=user.id,previousAccessToken=access_token.accesstoken))
                    active = user.accountStatus==AccountStatus.ACTIVE
                    token = create_jwt_token(access_token=access_token.accesstoken,user_id=user.id,user_type="USER",is_activated=active)
                    user.access_token= token
                    user.refresh_token = refresh_token.refreshtoken
                    await delete_access_token(accessToken=expired_access_token)
                    await delete_refresh_token(refreshToken=user_refresh_data.refresh_token)
                    return user
     
        await delete_refresh_token(refreshToken=user_refresh_data.refresh_token)
        await delete_access_token(accessToken=expired_access_token)
  
    raise HTTPException(status_code=400,detail="Invalid refresh token ")  
        
async def remove_user(user_id: str):
    """deletes a field from the database and removes UserCreateobject 

    Raises:
        HTTPException 400: Invalid user ID format
        HTTPException 404:  User not found
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    filter_dict = {"_id": ObjectId(user_id)}
    result = await delete_user(filter_dict)
    await delete_all_tokens_with_user_id(userId=user_id)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")


async def retrieve_user_by_user_id(id: str) -> UserOut:
    """Retrieves user object based specific Id 

    Raises:
        HTTPException 404(not found): if  User not found in the db
        HTTPException 400(bad request): if  Invalid user ID format

    Returns:
        _type_: UserOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    filter_dict = {"_id": ObjectId(id)}
    result = await get_user(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return result


async def retrieve_users(start=0,stop=100) -> List[UserOut]:
    """Retrieves UserOut Objects in a list

    Returns:
        _type_: UserOut
    """
    return await get_users(start=start,stop=stop)

async def update_user_by_id(driver_id: str, driver_data: UserUpdate,is_password_getting_changed:bool=False) -> UserOut:
    """updates an entry of driver in the database

    Raises:
        HTTPException 404(not found): if Driver not found or update failed
        HTTPException 400(not found): Invalid driver ID format

    Returns:
        _type_: DriverOut
    """
    from celery_worker import celery_app
    if not ObjectId.is_valid(driver_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    filter_dict = {"_id": ObjectId(driver_id)}
    result = await update_user(filter_dict, driver_data)
    
    if not result:
        raise HTTPException(status_code=404, detail="Driver not found or update failed")
    if is_password_getting_changed==True:
        celery_result = celery_app.send_task("celery_worker.run_async_task",args=["delete_tokens",{"userId": driver_id} ])
    return result


async def logout_user(user_id: str):
    """
    Logs out a user by:
    - retrieving the user
    - revoking OAuth tokens (if any)
    - deleting all local access & refresh tokens

    All operations run concurrently.
    """

    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    async def get_user_task():
        return await get_user(filter_dict={"_id": ObjectId(user_id)})

    async def delete_tokens_task():
        await delete_all_tokens_with_user_id(userId=user_id)

    # Run DB fetch + token deletion in parallel
    user, _ = await asyncio.gather(
        get_user_task(),
        delete_tokens_task(),
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Revoke OAuth token AFTER user is known
    if user.loginType == LoginType.google and getattr(user, "oauth_access_token", None):
        try:
            await revoke_google_token(user.oauth_access_token)
        except Exception:
            # Never block logout if Google revoke fails
            pass

    return True







def _cache_key_for_reset_token(token: str) -> str:
    return f"pwreset:{token}"


async def _cache_reset_token(token: str, user_id: str, user_type: UserType, expires_at: datetime, used: bool):
    ttl_seconds = max(0, int((expires_at - datetime.utcnow()).total_seconds()))
    if ttl_seconds == 0:
        return
    await cache_set_json(
        key=_cache_key_for_reset_token(token),
        value={
            "userId": user_id,
            "userType": user_type.value,
            "expiresAt": int(expires_at.timestamp()),
            "used": used,
        },
        ttl_seconds=ttl_seconds,
    )


async def _get_cached_reset_token(token: str):
    cached = await cache_get_json(_cache_key_for_reset_token(token))
    if not cached:
        return None
    return cached


async def get_reset_token_state(token: str):
    cached = await _get_cached_reset_token(token)
    if cached:
        return cached

    db_token = await get_reset_token(filter_dict={"token": token})
    if not db_token or db_token.expiresAt is None:
        return None

    await _cache_reset_token(
        token=token,
        user_id=db_token.userId,
        user_type=db_token.userType,
        expires_at=db_token.expiresAt,
        used=db_token.used,
    )
    return {
        "userId": db_token.userId,
        "userType": db_token.userType.value,
        "expiresAt": int(db_token.expiresAt.timestamp()),
        "used": db_token.used,
    }


async def user_reset_password_intiation(
    user_details: ResetPasswordInitiation,
    base_url: str,
) -> ResetPasswordInitiationResponse:

    email = user_details.email.strip()
    user = await get_user(
        filter_dict={"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
    )
    if user:
        reset_token = secrets.token_urlsafe(32)
        token = ResetTokenBase(
            userId=user.id,
            userType=UserType.member,
            token=reset_token,
            used=False,
        )
        reset_token_create = ResetTokenCreate(**token.model_dump())
        db_token = await create_reset_token(reset_token_data=reset_token_create)
        if db_token.expiresAt is not None:
            await _cache_reset_token(
                token=reset_token,
                user_id=db_token.userId,
                user_type=db_token.userType,
                expires_at=db_token.expiresAt,
                used=db_token.used,
            )
        landing_url = f"{base_url.rstrip('/')}/users/auth/reset-password?reset_token={reset_token}"
        success = send_password_reset_link(user_email=email, link=landing_url)
        if success != 0:
            raise HTTPException(status_code=500, detail="Reset link did not send to the user email")

    return ResetPasswordInitiationResponse(
        message="If the email exists, a reset link has been sent."
    )
 
 
async def user_reset_password_conclusion(
    user_details: ResetPasswordConclusion
) -> bool:

    if not user_details.resetToken or len(user_details.resetToken) < 10:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    token_state = await get_reset_token_state(user_details.resetToken) # type: ignore
    if not token_state:
        raise HTTPException(status_code=404,detail="Reset token not found")

    if token_state["userType"] != UserType.member.value:
        raise HTTPException(status_code=403,detail="Reset token is not for a member")

    if token_state["used"]:
        raise HTTPException(status_code=400,detail="Reset token already used")

    if token_state["expiresAt"] <= int(datetime.utcnow().timestamp()):
        raise HTTPException(status_code=400,detail="Reset token expired")

    driver_update = UserUpdatePassword(
        password=user_details.password
    )

    result = await update_user_by_id(
        driver_id=token_state["userId"],
        driver_data=driver_update,
        is_password_getting_changed=True
    )

    if not result:
        raise HTTPException(status_code=500,detail="Failed to update user password")

    await mark_reset_token_used(filter_dict={"token": user_details.resetToken})
    await _cache_reset_token(
        token=user_details.resetToken,
        user_id=token_state["userId"],
        user_type=UserType.member,
        expires_at=datetime.utcfromtimestamp(token_state["expiresAt"]),
        used=True,
    )

    return True
