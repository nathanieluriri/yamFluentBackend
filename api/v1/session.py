
import asyncio
import io
import logging
import os
import random
import time
from fastapi import APIRouter, Depends, File, HTTPException, Query, Path, UploadFile, status
from typing import List, Optional, Tuple
import json
from openai import (
    APIError,
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from schemas.imports import ScenarioName
from schemas.response_schema import APIResponse
from schemas.session import (
    SessionBaseRequest,
    SessionCreate,
    SessionOut,
    SessionBase,
    SessionUpdate,
    ListOfSessionOut,
)
from schemas.tokens_schema import accessTokenOut
from security.auth import verify_admin_token, verify_token_user_role
from services.session_service import (
    add_session,
    remove_session,
    retrieve_sessions,
    retrieve_session_summaries,
    retrieve_session_by_session_id,
    update_session_by_id,
)
from controller.script_generation.clients import get_openai_client

router = APIRouter(prefix="/sessions", tags=["Sessions"])
logger = logging.getLogger(__name__)

_LIMIT_TEST_PROMPT_PARAGRAPH = (
    "You are reviewing a long-form brief about sustainable city planning and the "
    "tradeoffs between density, transit access, green space, and housing affordability. "
    "Summarize the key tensions, then outline a practical policy framework with clear "
    "priorities, stakeholder impacts, and measurable outcomes. Consider economic, social, "
    "and environmental constraints, include potential counterarguments, and suggest how "
    "to evaluate progress over a five-year period. Keep the tone analytical and avoid "
    "marketing language while retaining specific, grounded recommendations for decision makers."
)


def _build_large_prompt() -> str:
    return "\n\n".join([_LIMIT_TEST_PROMPT_PARAGRAPH] * 12)


def _extract_openai_error_type(exc: Exception) -> Optional[str]:
    for attr in ("type", "code"):
        value = getattr(exc, attr, None)
        if value:
            return str(value)
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error") or {}
        if isinstance(error, dict):
            return error.get("type") or error.get("code")
    message = str(exc).lower()
    if "insufficient_quota" in message:
        return "insufficient_quota"
    return None


def _is_insufficient_quota(exc: Exception) -> bool:
    return _extract_openai_error_type(exc) == "insufficient_quota"


def _extract_usage_tokens(response) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return None, None, None
    if isinstance(usage, dict):
        return (
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
        )
    return (
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
        getattr(usage, "total_tokens", None),
    )


async def _call_with_rate_limit_retry(
    coro_factory,
    endpoint_label: str,
    max_retries: int,
    base_delay: float,
    max_delay: float,
) -> Tuple[Optional[object], Optional[str]]:
    attempt = 0
    while True:
        try:
            return await coro_factory(), None
        except RateLimitError as exc:
            if _is_insufficient_quota(exc):
                logger.error(
                    "OpenAI %s insufficient_quota detected; no retry.", endpoint_label
                )
                return None, "quota_exceeded"
            attempt += 1
            if attempt > max_retries:
                logger.error("OpenAI %s rate limit after retries.", endpoint_label)
                return None, "rate_limited"
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, 0.3)
            logger.warning(
                "OpenAI %s rate limited (attempt %s/%s). Retrying in %.2fs.",
                endpoint_label,
                attempt,
                max_retries,
                delay,
            )
            await asyncio.sleep(delay)
        except APITimeoutError:
            logger.error("OpenAI %s timeout detected.", endpoint_label)
            return None, "timeout"
        except APIConnectionError:
            logger.error("OpenAI %s connection error detected.", endpoint_label)
            return None, "connection_error"
        except APIError as exc:
            if _is_insufficient_quota(exc):
                logger.error(
                    "OpenAI %s insufficient_quota detected; no retry.", endpoint_label
                )
                return None, "quota_exceeded"
            status = getattr(exc, "status_code", None)
            if status == 429:
                attempt += 1
                if attempt > max_retries:
                    logger.error("OpenAI %s rate limit after retries.", endpoint_label)
                    return None, "rate_limited"
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                delay += random.uniform(0, 0.3)
                logger.warning(
                    "OpenAI %s rate limited (attempt %s/%s). Retrying in %.2fs.",
                    endpoint_label,
                    attempt,
                    max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            logger.error("OpenAI %s APIError: %s", endpoint_label, exc)
            return None, "api_error"
        except asyncio.TimeoutError:
            logger.error("OpenAI %s asyncio timeout detected.", endpoint_label)
            return None, "timeout"
        except Exception as exc:
            logger.error("OpenAI %s unexpected error: %s", endpoint_label, exc)
            return None, "unknown_error"


def _load_audio_bytes(path: str) -> bytes:
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio sample path is required for speech-to-text test.",
        )
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio sample file not found: {path}",
        )
    with open(path, "rb") as handle:
        return handle.read()

async def _test_openai_key() -> dict:
    client = AsyncOpenAI()
    models = await client.models.list()
    data = list(models.data or [])
    sample = data[0].id if data else None
    return {"model_count": len(data), "sample_model": sample}


# ------------------------------
# List Sessions (with pagination and filtering)
# ------------------------------
@router.get("/", response_model=APIResponse[List[ListOfSessionOut]],dependencies=[Depends(verify_token_user_role)],)
async def list_sessions(
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for page-based pagination (0-indexed)"),
    
    # New: Filter parameter expects a JSON string
    filters: Optional[ScenarioName] = Query(None, description="Optional Scenario name string "),
    token:accessTokenOut = Depends(verify_token_user_role)
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
        items = await retrieve_session_summaries(filters=parsed_filters, start=start, stop=stop,user_id=token.userId)
        return APIResponse(status_code=200, data=items, detail="Fetched successfully")

    # Case 2: Use page_number if provided
    elif page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative.")
        
        start_index = page_number * PAGE_SIZE
        stop_index = start_index + PAGE_SIZE
        # Pass filters to the service layer
        items = await retrieve_session_summaries(filters=parsed_filters, start=start_index, stop=stop_index,user_id=token.userId)
        return APIResponse(status_code=200, data=items, detail=f"Fetched page {page_number} successfully")

    # Case 3: Default (no params)
    else:
        # Pass filters to the service layer
        items = await retrieve_session_summaries(filters=parsed_filters, start=0, stop=100,user_id=token.userId)
        detail_msg = "Fetched first 100 records successfully"
        if parsed_filters:
            # If filters were applied, adjust the detail message
            detail_msg = f"Fetched first 100 records successfully (with filters applied)"
        return APIResponse(status_code=200, data=items, detail=detail_msg)


# ------------------------------
# Retrieve a single Session
# ------------------------------
@router.get("/{id}",dependencies=[Depends(verify_token_user_role)], response_model=APIResponse[SessionOut])
async def get_session_by_id(
    id: str = Path(..., description="session ID to fetch specific item"),
     token:accessTokenOut = Depends(verify_token_user_role)
):
    """
    Retrieves a single Session by its ID.
    """
    item = await retrieve_session_by_session_id(id=id,user_id=token.userId)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found")
    return APIResponse(status_code=200, data=item, detail="session item fetched")


# ------------------------------
# Create a new Session
# ------------------------------
# Uses SessionBase for input (correctly)
@router.post("/", dependencies=[Depends(verify_token_user_role)], response_model=APIResponse[SessionOut], status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionBaseRequest,token:accessTokenOut = Depends(verify_token_user_role)):
    """
    Creates a new Session.
    """
    # Creates SessionCreate object which includes date_created/last_updated
    new_data = SessionBase(**payload.model_dump(),userId=token.userId) 
    new_item = await add_session(new_data)
    if not new_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create session")
    
    return APIResponse(status_code=201, data=new_item, detail=f"Session created successfully")


# ------------------------------
# Update an existing Session
# ------------------------------
# Uses PATCH for partial update (correctly)
@router.patch("/{id}/{turn_index}", response_model=APIResponse[SessionOut])
async def users_turn_to_speak(
    turn_index:int,
    id: str = Path(..., description="ID of the {db_name} to update"),
    audio: UploadFile = File(..., description="User audio MP3"),
    token:accessTokenOut = Depends(verify_token_user_role)
):
    """
    Updates an existing Session by its ID.
    Assumes the service layer handles partial updates (e.g., ignores None fields in payload).
    """
     
    if audio.content_type not in ("audio/mpeg", "audio/mp3"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Audio must be an MP3 (audio/mpeg)."
        )
         
    updated_item = await update_session_by_id(session_id=id,user_id=token.userId,turn_index=turn_index,audio=audio  )
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found or update failed")
    
    return APIResponse(status_code=200, data=updated_item, detail=f"Session updated successfully")


@router.get("/openai/test", dependencies=[Depends(verify_token_user_role)])
async def test_openai_api_key(token: accessTokenOut = Depends(verify_token_user_role)):
    """
    Lightweight API key check using OpenAI's models list endpoint.
    """
    try:
        payload = await _test_openai_key()
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key")
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except APIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="OpenAI API key test failed")
    return APIResponse(status_code=200, data=payload, detail="OpenAI API key is valid")


@router.get("/openai/info", dependencies=[Depends(verify_token_user_role)])
async def openai_config_info(token: accessTokenOut = Depends(verify_token_user_role)):
    """
    Returns OpenAI org/project configuration as seen from environment variables.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    payload = {
        "openai_org_id": os.getenv("OPENAI_ORG_ID"),
        "openai_project_id": os.getenv("OPENAI_PROJECT_ID"),
        "openai_api_key_present": bool(api_key),
        "openai_api_key_prefix": f"{api_key[:6]}..." if api_key else None,
    }
    return APIResponse(status_code=200, data=payload, detail="OpenAI config info")


@router.get("/test/limit", dependencies=[Depends(verify_token_user_role)])
async def test_openai_limits(
    text_concurrency: int = Query(3, ge=1, le=50),
    text_batches: int = Query(2, ge=1, le=20),
    speech_concurrency: int = Query(2, ge=1, le=50),
    speech_batches: int = Query(2, ge=1, le=20),
    batch_delay_s: float = Query(1.0, ge=0.0, le=30.0),
    text_max_tokens: int = Query(1024, ge=64, le=4096),
    audio_path: Optional[str] = Query(
        None, description="Path to local WAV/MP3 sample for speech-to-text test."
    ),
    token: accessTokenOut = Depends(verify_token_user_role),
):
    """
    Stress test OpenAI rate limits for text generation and speech-to-text endpoints.
    """
    client = get_openai_client()
    text_model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    speech_model = os.getenv("OPENAI_ASR_MODEL", "gpt-4o-mini-transcribe")
    max_retries = int(os.getenv("OPENAI_LIMIT_TEST_MAX_RETRIES", "2"))
    base_delay = float(os.getenv("OPENAI_LIMIT_TEST_BASE_DELAY", "0.8"))
    max_delay = float(os.getenv("OPENAI_LIMIT_TEST_MAX_DELAY", "6"))
    prompt = _build_large_prompt()
    audio_sample_path = audio_path or os.getenv("OPENAI_STT_SAMPLE_PATH")
    audio_bytes = _load_audio_bytes(audio_sample_path)

    async def _run_text_request(request_id: int) -> dict:
        start = time.monotonic()
        response, error_kind = await _call_with_rate_limit_retry(
            lambda: client.chat.completions.create(
                model=text_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=text_max_tokens,
                temperature=0.2,
            ),
            endpoint_label="chat.completions",
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
        )
        elapsed = time.monotonic() - start
        if response is not None:
            prompt_tokens, completion_tokens, total_tokens = _extract_usage_tokens(
                response
            )
            logger.info(
                "OpenAI chat.completions success request=%s latency=%.2fs prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                request_id,
                elapsed,
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )
            return {"success": True, "rate_limited": False, "quota_exceeded": False}
        logger.warning(
            "OpenAI chat.completions failed request=%s latency=%.2fs error=%s",
            request_id,
            elapsed,
            error_kind,
        )
        return {
            "success": False,
            "rate_limited": error_kind == "rate_limited",
            "quota_exceeded": error_kind == "quota_exceeded",
        }

    async def _run_speech_request(request_id: int) -> dict:
        start = time.monotonic()
        def _make_audio_call():
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = os.path.basename(audio_sample_path or "sample.wav")
            return client.audio.transcriptions.create(
                model=speech_model,
                file=audio_file,
                response_format="json",
            )

        response, error_kind = await _call_with_rate_limit_retry(
            _make_audio_call,
            endpoint_label="audio.transcriptions",
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
        )
        elapsed = time.monotonic() - start
        if response is not None:
            logger.info(
                "OpenAI audio.transcriptions success request=%s latency=%.2fs",
                request_id,
                elapsed,
            )
            return {"success": True, "rate_limited": False, "quota_exceeded": False}
        logger.warning(
            "OpenAI audio.transcriptions failed request=%s latency=%.2fs error=%s",
            request_id,
            elapsed,
            error_kind,
        )
        return {
            "success": False,
            "rate_limited": error_kind == "rate_limited",
            "quota_exceeded": error_kind == "quota_exceeded",
        }

    async def _run_batches(total_batches: int, concurrency: int, runner) -> List[dict]:
        results: List[dict] = []
        for batch_index in range(total_batches):
            tasks = [
                asyncio.create_task(runner(batch_index * concurrency + offset))
                for offset in range(concurrency)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            if batch_delay_s > 0 and batch_index < total_batches - 1:
                await asyncio.sleep(batch_delay_s)
        return results

    text_results = await _run_batches(text_batches, text_concurrency, _run_text_request)
    speech_results = await _run_batches(
        speech_batches, speech_concurrency, _run_speech_request
    )

    def _summarize(results: List[dict]) -> dict:
        total = len(results)
        success = sum(1 for item in results if item.get("success"))
        rate_limited = sum(1 for item in results if item.get("rate_limited"))
        quota_exceeded = sum(1 for item in results if item.get("quota_exceeded"))
        return {
            "total": total,
            "success": success,
            "rate_limited": rate_limited,
            "quota_exceeded": quota_exceeded,
        }

    return {
        "text_generation": _summarize(text_results),
        "speech_to_text": _summarize(speech_results),
    }

