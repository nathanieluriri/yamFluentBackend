import asyncio
import os
import uuid

from fastapi import HTTPException
from openai import AsyncOpenAI

from controller.script_generation.clients import (
    build_public_r2_url,
    estimate_tokens_from_texts,
    get_r2_client,
    openai_request_with_retries,
)


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


async def generate_audio_url(
    client: AsyncOpenAI,
    text: str,
    voice: str,
    key_prefix: str,
) -> str:
    tts_model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    estimated_tokens = estimate_tokens_from_texts([text])
    response = await openai_request_with_retries(
        lambda: client.audio.speech.create(
            model=tts_model,
            voice=voice,
            input=text,
            response_format="mp3",
        ),
        estimated_tokens=estimated_tokens,
    )
    response_url = getattr(response, "url", None)
    if isinstance(response_url, str) and response_url.startswith("http"):
        return response_url
    audio_bytes = await response_to_bytes(response)
    key = f"{key_prefix}/{uuid.uuid4().hex}.mp3"
    return await upload_audio_bytes(audio_bytes, key)
