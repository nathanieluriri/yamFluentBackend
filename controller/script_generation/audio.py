import asyncio
import os
import uuid
from typing import List, Optional
from urllib.parse import unquote, urlparse

from fastapi import HTTPException
from openai import AsyncOpenAI

from controller.script_generation.clients import (
    build_public_r2_url,
    estimate_tokens_from_texts,
    get_r2_client,
    openai_request_with_retries,
)
from controller.script_generation.model_config import TTS_MODEL


async def response_to_bytes(response: object) -> bytes:
    if isinstance(response, (bytes, bytearray)):
        return bytes(response)
    content = getattr(response, "content", None)
    if isinstance(content, (bytes, bytearray)):
        return bytes(content)
    read = getattr(response, "read", None)
    if read:
        data = read()
        if asyncio.iscoroutine(data):
            return await data
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
    raise ValueError("Unable to extract audio bytes from response")


async def upload_audio_bytes(audio_bytes: bytes, key: str) -> str:
    bucket = os.getenv("CLOUDFLARE_R2_BUCKET")
    if not bucket:
        raise HTTPException(
            status_code=500,
            detail="Missing CLOUDFLARE_R2_BUCKET environment variable.",
        )
    client = get_r2_client()
    await asyncio.to_thread(
        client.put_object,
        Bucket=bucket,
        Key=key,
        Body=audio_bytes,
        ContentType="audio/mpeg",
    )
    return build_public_r2_url(bucket, key)


def _strip_prefix(value: str, prefix: str) -> Optional[str]:
    if not prefix:
        return None
    if value.startswith(prefix):
        return value[len(prefix):].lstrip("/")
    return None


def _extract_r2_key(audio_url: str) -> Optional[str]:
    if not audio_url:
        return None
    public_base = os.getenv("CLOUDFLARE_R2_PUBLIC_URL", "").rstrip("/")
    endpoint = os.getenv("CLOUDFLARE_R2_ENDPOINT", "").rstrip("/")
    bucket = os.getenv("CLOUDFLARE_R2_BUCKET", "")

    key = _strip_prefix(audio_url, public_base)
    if key is not None:
        return unquote(key)

    if endpoint and bucket:
        key = _strip_prefix(audio_url, f"{endpoint}/{bucket}")
        if key is not None:
            return unquote(key)

    parsed = urlparse(audio_url)
    if parsed.scheme:
        path = parsed.path.lstrip("/")
        if bucket and path.startswith(f"{bucket}/"):
            return unquote(path[len(bucket) + 1 :])
        return unquote(path) if path else None

    return audio_url.lstrip("/")


def extract_r2_key(audio_url: str) -> Optional[str]:
    return _extract_r2_key(audio_url)


async def delete_audio_by_urls(audio_urls: List[str]) -> int:
    bucket = os.getenv("CLOUDFLARE_R2_BUCKET")
    if not bucket:
        return 0
    client = get_r2_client()
    deleted = 0
    for audio_url in audio_urls:
        key = _extract_r2_key(audio_url)
        if not key:
            continue
        await asyncio.to_thread(
            client.delete_object,
            Bucket=bucket,
            Key=key,
        )
        deleted += 1
    return deleted


async def generate_audio_url(
    client: AsyncOpenAI,
    text: str,
    voice: str,
    key_prefix: str,
) -> str:
    tts_model = os.getenv("OPENAI_TTS_MODEL", TTS_MODEL)
    estimated_tokens = estimate_tokens_from_texts([text])
    response = await openai_request_with_retries(
        lambda: client.audio.speech.create(
            model=tts_model,
            voice=voice,
            input=text,
            response_format="mp3",
        ), # pyright: ignore[reportUnknownLambdaType]
        estimated_tokens=estimated_tokens,
    )
    response_url = getattr(response, "url", None)
    if isinstance(response_url, str) and response_url.startswith("http"):
        return response_url
    audio_bytes = await response_to_bytes(response)
    key = f"{key_prefix}/{uuid.uuid4().hex}.mp3"
    return await upload_audio_bytes(audio_bytes, key)
