from datetime import datetime, timezone
from bson import ObjectId

from core.redis_cache import cache_db
from core.scheduler import scheduler
from repositories.session import delete_session, get_session


async def cleanup_incomplete_session(session_id: str, user_id: str, date_created: int) -> None:
    try:
        if not session_id or not user_id or not date_created:
            return
        if not ObjectId.is_valid(session_id):
            return
        session = await get_session(filter_dict={"_id": ObjectId(session_id), "userId": user_id})
        if not session or session.date_created is None:
            return
        if int(datetime.now(tz=timezone.utc).timestamp()) - session.date_created < 3600:
            _clear_cleanup_enqueue_lock(session_id, session.date_created)
            schedule_cleanup_incomplete_session(session_id, user_id, session.date_created)
            return
        script = getattr(session, "script", None)
        turns = getattr(script, "turns", None) if script else None
        if not turns:
            return
        all_scores_null = all(getattr(turn, "score", None) is None for turn in turns)
        if all_scores_null:
            await delete_session({"_id": ObjectId(session_id), "userId": user_id})
    except Exception:
        return


def schedule_cleanup_incomplete_session(session_id: str, user_id: str, date_created: int) -> None:
    if not session_id or not user_id or not date_created:
        return
    run_time = datetime.fromtimestamp(date_created + 3600, tz=timezone.utc)
    job_id = f"cleanup_session_{session_id}"
    kwargs = {
        "session_id": session_id,
        "user_id": user_id,
        "date_created": date_created,
    }
    scheduler.add_job(
        _enqueue_cleanup_task,
        "date",
        run_date=run_time,
        args=[kwargs],
        id=job_id,
        replace_existing=True,
    )


def _enqueue_cleanup_task(kwargs: dict) -> None:
    from celery_worker import celery_app

    if not _acquire_cleanup_enqueue_lock(kwargs):
        return
    celery_app.send_task(
        "celery_worker.run_async_task",
        args=["cleanup_incomplete_session", kwargs],
    )


def _cleanup_enqueue_lock_key(session_id: str, date_created: int) -> str:
    return f"cleanup_enqueue:{session_id}:{date_created}"


def _acquire_cleanup_enqueue_lock(kwargs: dict) -> bool:
    try:
        session_id = kwargs.get("session_id")
        date_created = kwargs.get("date_created")
        if not session_id or not date_created:
            return False
        key = _cleanup_enqueue_lock_key(session_id, date_created)
        ttl_seconds = 7200
        return bool(cache_db.set(key, "1", nx=True, ex=ttl_seconds))
    except Exception:
        return False


def _clear_cleanup_enqueue_lock(session_id: str, date_created: int) -> None:
    try:
        key = _cleanup_enqueue_lock_key(session_id, date_created)
        cache_db.delete(key)
    except Exception:
        return


__all__ = [
    "cleanup_incomplete_session",
    "schedule_cleanup_incomplete_session",
]
