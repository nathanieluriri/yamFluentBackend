import asyncio
import os
import random
import time
from collections import deque
from typing import Optional

from fastapi import HTTPException
from openai import APIError, AsyncOpenAI, RateLimitError

_openai_client: Optional[AsyncOpenAI] = None
_r2_client = None
_openai_semaphore: Optional[asyncio.Semaphore] = None
_openai_rate_lock = asyncio.Lock()
_openai_last_call = 0.0
_openai_window_lock = asyncio.Lock()
_openai_request_window = deque()
_openai_token_window = deque()


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI()
    return _openai_client


def get_openai_semaphore() -> asyncio.Semaphore:
    global _openai_semaphore
    if _openai_semaphore is None:
        max_concurrency = int(os.getenv("OPENAI_MAX_CONCURRENCY", "1"))
        _openai_semaphore = asyncio.Semaphore(max(1, max_concurrency))
    return _openai_semaphore


async def apply_openai_rate_limit() -> None:
    min_interval_ms = int(os.getenv("OPENAI_MIN_INTERVAL_MS", "800"))
    if min_interval_ms <= 0:
        return
    global _openai_last_call
    async with _openai_rate_lock:
        now = time.monotonic()
        wait_s = (min_interval_ms / 1000) - (now - _openai_last_call)
        if wait_s > 0:
            await asyncio.sleep(wait_s)
        _openai_last_call = time.monotonic()


def estimate_tokens_from_texts(texts: list[str]) -> int:
    total_chars = sum(len(text or "") for text in texts)
    return max(1, total_chars // 4)


async def _wait_for_quota(estimated_tokens: int) -> None:
    rpm_limit = int(os.getenv("OPENAI_RPM_LIMIT", "60"))
    tpm_limit = int(os.getenv("OPENAI_TPM_LIMIT", "20000"))
    now = time.monotonic()
    async with _openai_window_lock:
        while _openai_request_window and now - _openai_request_window[0] > 60:
            _openai_request_window.popleft()
        while _openai_token_window and now - _openai_token_window[0][0] > 60:
            _openai_token_window.popleft()
        req_count = len(_openai_request_window)
        token_count = sum(tokens for _, tokens in _openai_token_window)
        if req_count >= rpm_limit or token_count + estimated_tokens > tpm_limit:
            oldest_req = _openai_request_window[0] if _openai_request_window else now
            oldest_tok = _openai_token_window[0][0] if _openai_token_window else now
            wait_s = max(0.0, 60 - min(now - oldest_req, now - oldest_tok))
            await asyncio.sleep(wait_s + 0.05)
            return await _wait_for_quota(estimated_tokens)
        _openai_request_window.append(now)
        _openai_token_window.append((now, estimated_tokens))


async def openai_request_with_retries(coro_factory, estimated_tokens: int = 0):
    max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "5"))
    base_delay = float(os.getenv("OPENAI_RETRY_BASE_DELAY", "0.8"))
    max_delay = float(os.getenv("OPENAI_RETRY_MAX_DELAY", "10"))
    attempt = 0
    while True:
        try:
            async with get_openai_semaphore():
                await apply_openai_rate_limit()
                await _wait_for_quota(max(0, estimated_tokens))
                return await coro_factory()
        except RateLimitError as exc:
            attempt += 1
            if attempt > max_retries:
                raise
            retry_after = None
            if hasattr(exc, "response") and exc.response is not None:
                retry_after = exc.response.headers.get("retry-after")
            delay = float(retry_after) if retry_after else min(
                max_delay, base_delay * (2 ** (attempt - 1))
            )
            delay += random.uniform(0, 0.25)
            await asyncio.sleep(delay)
        except APIError as exc:
            status = getattr(exc, "status_code", None)
            if status != 429:
                raise
            attempt += 1
            if attempt > max_retries:
                raise
            retry_after = None
            if hasattr(exc, "response") and exc.response is not None:
                retry_after = exc.response.headers.get("retry-after")
            delay = float(retry_after) if retry_after else min(
                max_delay, base_delay * (2 ** (attempt - 1))
            )
            delay += random.uniform(0, 0.25)
            await asyncio.sleep(delay)


def get_r2_client():
    global _r2_client
    if _r2_client is None:
        try:
            import boto3
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail="boto3 is required for Cloudflare R2 uploads but is not installed.",
            ) from exc
        endpoint = os.getenv("CLOUDFLARE_R2_ENDPOINT")
        access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID") or os.getenv(
            "AWS_ACCESS_KEY_ID"
        )
        secret_key = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY") or os.getenv(
            "AWS_SECRET_ACCESS_KEY"
        )
        if not endpoint or not access_key or not secret_key:
            raise HTTPException(
                status_code=500,
                detail="Missing Cloudflare R2 credentials in environment variables.",
            )
        _r2_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=os.getenv("CLOUDFLARE_R2_REGION", "auto"),
        )
    return _r2_client


def build_public_r2_url(bucket: str, key: str) -> str:
    public_base = os.getenv("CLOUDFLARE_R2_PUBLIC_URL")
    if public_base:
        return f"{public_base.rstrip('/')}/{key}"
    endpoint = os.getenv("CLOUDFLARE_R2_ENDPOINT", "").rstrip("/")
    return f"{endpoint}/{bucket}/{key}" if endpoint else key
