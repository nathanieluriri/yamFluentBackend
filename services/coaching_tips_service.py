import json
import os
import time
from collections import Counter
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException

from controller.script_generation.clients import (
    estimate_tokens_from_texts,
    get_openai_client,
    openai_request_with_retries,
)
from repositories.coaching_tips import (
    DuplicateKeyError,
    create_coaching_tip,
    ensure_coaching_tip_indexes,
    get_coaching_tip_by_id,
    get_coaching_tip_by_session,
    list_coaching_tips,
)
from repositories.session import get_session
from repositories.user_repo import get_user
from schemas.coaching_tips import (
    CoachingTipCreate,
    CoachingTipCreateRequest,
    CoachingTipListItem,
    CoachingTipResponse,
)
from schemas.session import SessionOut
from schemas.tokens_schema import accessTokenOut
from schemas.user_schema import UserOut


def _safe_model_dump(model: Any) -> Dict[str, Any]:
    if model is None:
        return {}
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return dict(model)


def _aggregate_turn_data(session: SessionOut) -> Dict[str, Any]:
    turns = getattr(session, "script", None)
    turns = getattr(turns, "turns", None) or []
    turn_summaries: List[Dict[str, Any]] = []
    mispronounced_counter: Counter[str] = Counter()
    far_substitutions: Counter[str] = Counter()
    insertions = deletions = 0
    wers: List[float] = []

    for turn in turns:
        if getattr(turn, "role", None) != "user":
            continue

        score = _safe_model_dump(getattr(turn, "score", None))
        mispronounced_words = getattr(turn, "mispronounced_words", None) or []
        speech_analysis = getattr(turn, "speech_analysis", None)
        speech_analysis_dump = speech_analysis.model_dump() if speech_analysis else None

        for word in mispronounced_words:
            mispronounced_counter[word] += 1

        if speech_analysis:
            summary = speech_analysis.alignment_summary
            wers.append(getattr(summary, "wer", None) or 0.0)
            insertions += getattr(summary, "insertions", 0)
            deletions += getattr(summary, "deletions", 0)
            for diff in speech_analysis.ignored_differences:
                if getattr(diff, "ignored_because", "") == "too_far_from_expected":
                    key = diff.expected or diff.actual
                    if key:
                        far_substitutions[key] += 1
        turn_summaries.append(
            {
                "index": getattr(turn, "index", None),
                "expected_text": getattr(turn, "text", None),
                "score": score,
                "mispronounced_words": mispronounced_words,
                "speech_analysis": speech_analysis_dump,
            }
        )

    avg_wer = sum(wers) / max(1, len(wers))
    return {
        "turns": turn_summaries,
        "top_mispronounced": [w for w, _ in mispronounced_counter.most_common(5)],
        "far_substitutions": [w for w, _ in far_substitutions.most_common(5)],
        "insertions": insertions,
        "deletions": deletions,
        "avg_wer": avg_wer,
    }


def _build_prompt_context(
    profile: Optional[UserOut],
    session: SessionOut,
) -> Dict[str, Any]:
    profile_data = (
        _safe_model_dump(getattr(profile, "userPersonalProfilingData", None))
        if profile
        else None
    )
    turn_data = _aggregate_turn_data(session)
    script = getattr(session, "script", None)
    turn_count = len(getattr(script, "turns", []) or [])

    return {
        "profile": profile_data,
        "session": {
            "session_id": getattr(session, "id", None),
            "scenario": getattr(session, "scenario", None),
            "completed": getattr(session, "completed", None),
            "average_score": getattr(session, "average_score", None),
            "turn_count": turn_count,
        },
        "grading": turn_data,
    }


def _heuristic_tip(context: Dict[str, Any]) -> Dict[str, Any]:
    mispronounced = context.get("grading", {}).get("top_mispronounced") or []
    far = context.get("grading", {}).get("far_substitutions") or []
    practice_words = (mispronounced + far)[:5]
    tip_focus = ", ".join(practice_words[:2]) if practice_words else "clarity"
    tip_text = (
        f"Focus on clear sounds for {tip_focus}; slow slightly and repeat. "
        f"Practice: {', '.join(practice_words[:5])}" if practice_words else
        "Speak a bit slower and stress key consonants; practice with short words."
    )
    return {
        "tip_text": tip_text[:280],
        "practice_words": practice_words[:6] if practice_words else None,
    }


async def _call_openai_for_tip(prompt_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    client = get_openai_client()
    model_name = os.getenv("OPENAI_COACHING_TIP_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    prompt_version = os.getenv("COACHING_TIP_PROMPT_VERSION", "v1")
    system_prompt = (
        "You are a concise pronunciation coach. Using the learner profile, session scores, and "
        "speech alignment insights, write ONE actionable tip (<=280 chars). "
        "Add 2-6 single-word practice words if helpful. Avoid metrics or jargon. "
        "Return JSON only: {\"tip_text\": \"...\", \"practice_words\": [\"...\"]}."
    )
    user_content = json.dumps(
        {
            "version": prompt_version,
            "data": prompt_context,
        },
        ensure_ascii=False,
    )
    estimated_tokens = estimate_tokens_from_texts([system_prompt, user_content])
    try:
        response = await openai_request_with_retries(
            lambda: client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
                max_tokens=160,
            ), # pyright: ignore[reportUnknownLambdaType]
            estimated_tokens=estimated_tokens,
        )
    except Exception:
        return None
    content = (
        response.choices[0].message.content
        if getattr(response, "choices", None)
        else None
    )
    if not content:
        return None
    try:
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return None
        tip_text = str(parsed.get("tip_text") or "").strip()
        practice_words = parsed.get("practice_words")
        if practice_words is not None and not isinstance(practice_words, list):
            practice_words = None
        if tip_text:
            return {
                "tip_text": tip_text[:280],
                "practice_words": practice_words[:6] if practice_words else None,
                "provider_meta": {
                    "model": model_name,
                    "prompt_version": prompt_version,
                },
            }
    except Exception:
        return None
    return None


async def generate_or_get_coaching_tip(
    *,
    create_request: CoachingTipCreateRequest,
    user: accessTokenOut,
) -> CoachingTipResponse:
    if not ObjectId.is_valid(create_request.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    await ensure_coaching_tip_indexes()

    user_id = user.userId
    session_id = create_request.session_id
    existing = await get_coaching_tip_by_session(session_id=session_id, user_id=user_id)
    if existing:
        return existing

    session = await get_session(filter_dict={"_id": ObjectId(session_id), "userId": user_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Ensure lesson completed: all user turns must have audio + score
    script = getattr(session, "script", None)
    turns = getattr(script, "turns", None) or []
    for turn in turns:
        if getattr(turn, "role", None) != "user":
            continue
        if getattr(turn, "score", None) is None or getattr(turn, "user_audio_url", None) is None:
            raise HTTPException(
                status_code=400,
                detail="Coaching tip unavailable until all user turns have recorded audio and scores.",
            )
    user_profile = await get_user(filter_dict={"_id": ObjectId(user_id)})

    context = _build_prompt_context(user_profile, session)

    ai_result = await _call_openai_for_tip(context)
    if not ai_result:
        ai_result = _heuristic_tip(context)
        ai_result["provider_meta"] = {"model": "heuristic", "prompt_version": "v1"}
    tip_text = ai_result["tip_text"]
    practice_words = ai_result.get("practice_words")
    provider_meta = ai_result.get("provider_meta", {})

    feedback_payload = {
        "profile": context.get("profile"),
        "session": context.get("session"),
        "grading": context.get("grading"),
    }

    tip_data = CoachingTipCreate(
        session_id=session_id,
        user_id=user_id,
        tip_text=tip_text,
        practice_words=practice_words,
        provider_meta=provider_meta,
        feedback=feedback_payload,
        prompt_version=provider_meta.get("prompt_version", "v1"),
    )

    try:
        return await create_coaching_tip(tip_data)
    except DuplicateKeyError:
        # Race: tip was created after the initial check
        existing = await get_coaching_tip_by_session(session_id=session_id, user_id=user_id)
        if existing:
            return existing
        raise HTTPException(status_code=500, detail="Failed to create coaching tip due to duplicate key")


async def list_user_coaching_tips(
    *, user: accessTokenOut, start: int = 0, stop: int = 100
) -> List[CoachingTipListItem]:
    return await list_coaching_tips(user_id=user.userId, start=start, stop=stop)


async def get_user_coaching_tip_by_id(
    *, tip_id: str, user: accessTokenOut
) -> CoachingTipResponse:
    if not ObjectId.is_valid(tip_id):
        raise HTTPException(status_code=400, detail="Invalid coaching tip ID format")
    tip = await get_coaching_tip_by_id(tip_id=tip_id, user_id=user.userId)
    if not tip:
        raise HTTPException(status_code=404, detail="Coaching tip not found")
    return tip
