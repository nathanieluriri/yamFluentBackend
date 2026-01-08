# ============================================================================
# SESSION SERVICE
# ============================================================================
# This file was auto-generated on: 2026-01-05 17:43:29 WAT
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

from bson import ObjectId
from fastapi import HTTPException, UploadFile
from typing import List

from controller.session import (
    generate_script,
    calculate_turn_score,
    schedule_cleanup_incomplete_session,
)
from controller.script_generation.audio import delete_audio_by_urls
from repositories.session import (
    create_session,
    get_session,
    get_sessions,
    update_session,
    delete_session,
)
from schemas.session import (
    SessionBase,
    SessionCreate,
    SessionUpdate,
    SessionOut,
    ListOfSessionOut,
)


async def add_session(session_data: SessionBase) -> SessionOut:
    """Creates   SessionCreate Object from SessionBase by generating a script and then saving to the database also returns an object

    Returns:
        _type_: SessionOut
    """
    user_script=await generate_script(user_id=session_data.userId,scenario_name=session_data.scenario)
    session = SessionCreate(**session_data.model_dump(),script=user_script)    
    
    created = await create_session(session)
    schedule_cleanup_incomplete_session(
        session_id=created.id,
        user_id=created.userId,
        date_created=created.date_created,
    )
    return _with_stream_urls(created)


async def remove_session(session_id: str,user_id:str):
    """deletes a field from the database and removes SessionCreateobject 

    Raises:
        HTTPException 400: Invalid session ID format
        HTTPException 404:  Session not found
    """
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    filter_dict = {"_id": ObjectId(session_id), "userId": user_id}
    session = await get_session(filter_dict)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await delete_session(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_urls = set()
    script = getattr(session, "script", None)
    turns = getattr(script, "turns", None) if script else None
    if turns:
        for turn in turns:
            model_audio = getattr(turn, "model_audio_url", None)
            user_audio = getattr(turn, "user_audio_url", None)
            if model_audio:
                audio_urls.add(model_audio)
            if user_audio:
                audio_urls.add(user_audio)
    if audio_urls:
        try:
            await delete_audio_by_urls(list(audio_urls))
        except Exception:
            pass

    return True
    
    
    
async def retrieve_session_by_session_id(id: str,user_id:str) -> SessionOut:
    """Retrieves session object based specific Id 

    Raises:
        HTTPException 404(not found): if  Session not found in the db
        HTTPException 400(bad request): if  Invalid session ID format

    Returns:
        _type_: SessionOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    filter_dict = {"_id": ObjectId(id),"userId":user_id}
    result = await get_session(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return _with_stream_urls(result)


async def retrieve_sessions(user_id:str,start=0,stop=100,filters:dict=None) -> List[SessionOut]:
    """Retrieves SessionOut Objects in a list

    Returns:
        _type_: SessionOut
    """
    if filters is None:
        filters = {}
    filters["userId"] =user_id
    sessions = await get_sessions(filter_dict=filters, start=start, stop=stop)
    return [_with_stream_urls(session) for session in sessions]


async def delete_sessions_for_user(userId: str, batch_size: int = 100) -> int:
    """
    Deletes all sessions for a given user by listing sessions and removing them one by one.
    Intended for async execution via the celery run_async_task worker.
    """
    deleted = 0
    while True:
        sessions = await retrieve_sessions(user_id=userId, start=0, stop=batch_size)
        if not sessions:
            break
        for session in sessions:
            session_id = getattr(session, "id", None)
            if not session_id:
                continue
            try:
                await remove_session(session_id=session_id, user_id=userId)
                deleted += 1
            except HTTPException:
                continue
    return deleted


async def retrieve_session_summaries(
    user_id: str, start: int = 0, stop: int = 100, filters: dict = None
) -> List[ListOfSessionOut]:
    if filters is None:
        filters = {}
    filters["userId"] = user_id
    sessions = await get_sessions(filter_dict=filters, start=start, stop=stop)
    return [ListOfSessionOut(**session.model_dump()) for session in sessions]



async def update_session_by_id(session_id: str,user_id:str,turn_index:int,audio:UploadFile,  ) -> SessionOut:
    """updates an entry of session in the database

    Raises:
        HTTPException 404(not found): if Session not found or update failed
        HTTPException 400(not found): Invalid session ID format

    Returns:
        _type_: SessionOut
    """
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    existing_session = await get_session(filter_dict={"_id": ObjectId(session_id), "userId": user_id})
    if not existing_session:
        raise HTTPException(status_code=404, detail="Session not found or update failed")
    script = getattr(existing_session, "script", None)
    turns = getattr(script, "turns", None) if script else None
    if not turns or turn_index < 0 or turn_index >= len(turns):
        raise HTTPException(status_code=400, detail="Turn index out of range.")
    current_turn = turns[turn_index]
    if getattr(current_turn, "role", None) != "user":
        raise HTTPException(status_code=400, detail="Turn index does not correspond to a user turn.")
    score = await calculate_turn_score(
        session_id=session_id,
        user_id=user_id,
        turn_index=turn_index,
        audio=audio,
        session=existing_session,
        debug=False,
    )
    filter_dict = {"_id": ObjectId(session_id)}
    result = await update_session(filter_dict, score)

    if not result:
        raise HTTPException(status_code=404, detail="Session not found or update failed")

    return _with_stream_urls(result)


def _build_audio_stream_url(
    session_id: str,
    turn_index: int,
    audio_type: str,
) -> str:
    return f"/v1/users/sessions/audio/{session_id}/{turn_index}?audio_type={audio_type}"


def _with_stream_urls(session: SessionOut) -> SessionOut:
    session_id = getattr(session, "id", None)
    if not session_id:
        return session
    copy = session.model_copy(deep=True)
    script = getattr(copy, "script", None)
    turns = getattr(script, "turns", None) if script else None
    if not turns:
        return copy
    for idx, turn in enumerate(turns):
        turn_index = getattr(turn, "index", None)
        if turn_index is None:
            turn_index = idx
        model_audio_url = getattr(turn, "model_audio_url", None)
        if model_audio_url:
            turn.model_audio_url = _build_audio_stream_url(
                session_id=session_id,
                turn_index=turn_index,
                audio_type="model",
            )
        user_audio_url = getattr(turn, "user_audio_url", None)
        if user_audio_url:
            turn.user_audio_url = _build_audio_stream_url(
                session_id=session_id,
                turn_index=turn_index,
                audio_type="user",
            )
    return copy
