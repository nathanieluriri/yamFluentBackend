import io
import os
from typing import Any, Dict, Optional, Union

from bson import ObjectId
from fastapi import HTTPException, UploadFile

from controller.grading.scoring import MISPRONOUNCED_THRESHOLD, compute_scores
from controller.grading.text_align import tokenize
from controller.grading.speech_analysis_builder import build_speech_analysis
from controller.script_generation.audio import upload_audio_bytes
from controller.script_generation.clients import (
    get_openai_client,
    openai_request_with_retries,
)
from repositories.session import get_session, update_session
from schemas.imports import TurnScore
from schemas.session import ScriptTurnsUpdate, SessionUpdate, TurnUpdate


async def _audio_to_bytes(audio: Union[bytes, UploadFile]) -> bytes:
    if isinstance(audio, (bytes, bytearray)):
        return bytes(audio)
    return await audio.read()


async def _run_asr(audio_bytes: bytes) -> tuple[str, Dict[str, Any]]:
    client = get_openai_client()
    model_name = os.getenv("OPENAI_ASR_MODEL", "gpt-4o-mini-transcribe")
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "user_audio.mp3"
    estimated_tokens = int(os.getenv("OPENAI_ASR_TOKEN_ESTIMATE", "200"))
    response = await openai_request_with_retries(
        lambda: client.audio.transcriptions.create(
            model=model_name,
            file=audio_file,
            response_format="json",
        ),
        estimated_tokens=estimated_tokens,
    )
    transcript = getattr(response, "text", None)
    if not transcript:
        transcript = response.get("text") if isinstance(response, dict) else None
    if not transcript:
        raise HTTPException(status_code=500, detail="ASR failed to return transcript text.")
    meta: Dict[str, Any] = {
        "model": model_name,
        "estimated_tokens": estimated_tokens,
    }
    return str(transcript).strip(), meta


def _get_session_turn(session: Any, turn_index: int):
    script = getattr(session, "script", None)
    turns = getattr(script, "turns", None)
    if not turns or not isinstance(turns, list):
        raise HTTPException(status_code=500, detail="Session script turns not found.")
    if turn_index < 0 or turn_index >= len(turns):
        raise HTTPException(status_code=400, detail="Turn index out of range.")
    return turns[turn_index]


async def calculate_turn_score(
    session_id: str,
    user_id: str,
    turn_index: int,
    audio: Union[bytes, UploadFile],
    session: Optional[Any] = None,
    leniency: float = 1.0,
    debug: bool = False,
) -> SessionUpdate:
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    if session is None:
        session = await get_session(filter_dict={"_id": ObjectId(session_id), "userId": user_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    current_index = getattr(session.script.turns[turn_index], "index", None)
    if current_index is not None and current_index != turn_index:
        raise HTTPException(status_code=400, detail="Turn index does not match current session turn.")

    turn = _get_session_turn(session, turn_index)
    if getattr(turn, "role", None) != "user":
        raise HTTPException(status_code=400, detail="Turn index does not correspond to a user turn.")

    expected_text = getattr(turn, "text", None)
    if not expected_text:
        raise HTTPException(status_code=500, detail="Expected text missing for turn.")

    audio_bytes = await _audio_to_bytes(audio)
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio upload is empty.")
    transcript_text, asr_meta = await _run_asr(audio_bytes)

    expected_tokens = tokenize(expected_text)
    actual_tokens = tokenize(transcript_text)
    (
        confidence,
        fluency,
        hesitation,
        wer,
        filler_count,
        total_tokens,
        _alignment,
        mispronounced_words,
    ) = compute_scores(expected_tokens, actual_tokens, leniency)

    speech_analysis = build_speech_analysis(
        expected_text=expected_text,
        asr_text=transcript_text,
        expected_tokens=expected_tokens,
        actual_tokens=actual_tokens,
        alignment=_alignment,
        mispronounced_words=mispronounced_words,
        threshold=MISPRONOUNCED_THRESHOLD,
        asr_model=asr_meta.get("model"),
        asr_parameters=asr_meta,
    )

    user_audio_url: Optional[str] = None
    if audio_bytes:
        key_prefix = f"user-audio/{user_id}/{session_id}"
        key = f"{key_prefix}/turn-{turn_index}.mp3"
        user_audio_url = await upload_audio_bytes(audio_bytes, key)

    scores = TurnScore(
        confidence=confidence,
        fluency=fluency,
        hesitation=hesitation,
    )

    update_payload = SessionUpdate(
        script=ScriptTurnsUpdate(
            turns=[
                TurnUpdate(
                    index=turn_index,
                    score=scores,
                    mispronounced_words=mispronounced_words or None,
                    
                    user_audio_url=user_audio_url,
                    speech_analysis=speech_analysis,
                )
            ]
        )
    )
     

    response: Dict[str, Any] = {
        "transcript_text": transcript_text,
        "expected_text": expected_text,
        "mispronounced_words": mispronounced_words or None,
        "user_audio_url": user_audio_url,
        "scores": scores,
    }

    if debug:
        
        response.update(
            {
                "wer": wer,
                "filler_count": filler_count,
                "total_tokens": total_tokens,
                "speech_analysis": speech_analysis.model_dump(),
            }
        )
        
        print("response",response)

    return update_payload
