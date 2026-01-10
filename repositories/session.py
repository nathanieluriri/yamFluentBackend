from pymongo import ReturnDocument
from core.database import db
from fastapi import HTTPException,status
from typing import Any, Dict, List,Optional
from schemas.session import SessionUpdate, SessionCreate, SessionOut

async def create_session(session_data: SessionCreate) -> SessionOut:
    session_dict = session_data.model_dump()
    result =await db.sessions.insert_one(session_dict)
    result = await db.sessions.find_one(filter={"_id":result.inserted_id})
    returnable_result = SessionOut(**result)
    return returnable_result

async def get_session(filter_dict: dict) -> Optional[SessionOut]:
    try:
        result = await db.sessions.find_one(filter_dict)

        if result is None:
            return None

        return SessionOut(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching session: {str(e)}"
        )
    
async def get_sessions(filter_dict: dict = {},start=0,stop=100) -> List[SessionOut]:
    try:
        if filter_dict is None:
            filter_dict = {}

        cursor = (db.sessions.find(filter_dict)
        .skip(start)
        .limit(stop - start)
        )
        session_list = []

        async for doc in cursor:
            session_list.append(SessionOut(**doc))

        return session_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching sessions: {str(e)}"
        )
async def update_session(filter_dict: dict, session_data: SessionUpdate) -> SessionOut:
    payload = session_data.model_dump(exclude_none=True)

    update_doc: Dict[str, Any] = {"$set": {}}
    array_filters = []

    script = payload.pop("script", None)
    turns_updates = None
    if script:
        turns_updates = script.pop("turns", None)

        for k, v in script.items():
            update_doc["$set"][f"script.{k}"] = v

    for k, v in payload.items():
        update_doc["$set"][k] = v

    if turns_updates:
        for i, tu in enumerate(turns_updates):
            idx = tu.get("index")
            if idx is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each turn update must include 'index'."
                )

            alias = f"t{i}"
            array_filters.append({f"{alias}.index": idx, f"{alias}.role": "user"})

            for field_name, field_value in tu.items():
                if field_name == "index":
                    continue
                update_doc["$set"][f"script.turns.$[{alias}].{field_name}"] = field_value

    if not update_doc["$set"]:
        update_doc.pop("$set")

    if not update_doc:
        result = await db.sessions.find_one(filter_dict)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return SessionOut(**result)

    result = await db.sessions.find_one_and_update(
        filter_dict,
        update_doc,
        array_filters=array_filters if array_filters else None,
        return_document=ReturnDocument.AFTER
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return SessionOut(**result)

async def delete_session(filter_dict: dict):
    return await db.sessions.delete_one(filter_dict)
