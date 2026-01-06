import asyncio
import os
from typing import List, Optional

from bson import ObjectId
from fastapi import HTTPException

from controller.script_generation.audio import generate_audio_url
from controller.script_generation.clients import (
    apply_openai_rate_limit,
    get_openai_client,
    get_openai_semaphore,
)
from controller.script_generation.parsing import (
    is_strictly_alternating,
    parse_turns,
    trim_turns,
)
from controller.script_generation.prompts import (
    build_system_prompt,
    build_user_prompt,
    enum_value,
    normalize_learner_type,
    normalize_proficiency,
    turn_count_for_time,
)
from repositories.user_repo import get_user
from schemas.imports import AIGeneratedTurns, FluencyScript, Turn
from schemas.user_schema import UserPersonalProfilingData


async def generate_script(user_id: str, scenario_name: str) -> FluencyScript:
    # Helper function to create new AIGeneratedTurns according to scenario name and user info.
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await get_user(filter_dict={"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profiling: Optional[UserPersonalProfilingData] = getattr(
    user, "userPersonalProfilingData", None
)
    if not profiling:
        raise HTTPException(
            status_code=400,
            detail="Onboarding not completed. Please finish profiling to generate a script.",
        )

    daily_practice_time = enum_value(profiling.dailyPracticeTime)
    target_turns = turn_count_for_time(daily_practice_time)
    goals = [enum_value(goal) for goal in profiling.mainGoals]
    learner_type = normalize_learner_type(enum_value(profiling.learnerType))
    proficiency = normalize_proficiency(enum_value(profiling.currentProficiency))
    native_language = enum_value(profiling.nativeLanguage)

    system_prompt = build_system_prompt(
        target_turns=target_turns,
        goals=goals,
        learner_type=learner_type,
        proficiency=proficiency,
        native_language=native_language,
        scenario_name=scenario_name,
    )
    user_prompt = build_user_prompt(
        scenario_name=scenario_name,
        goals=goals,
        daily_practice_time=daily_practice_time,
    )

    client = get_openai_client()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def request_script(strict: bool) -> str:
        strict_suffix = (
            " Return ONLY valid JSON. No markdown, no commentary, no code fences."
            if strict
            else ""
        )
        async with get_openai_semaphore():
            await apply_openai_rate_limit()
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt + strict_suffix},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.6,
            )
        return (response.choices[0].message.content or "").strip()

    def validate_or_raise(raw_content: str) -> List[AIGeneratedTurns]:
        parsed = parse_turns(raw_content)
        turns = [AIGeneratedTurns(**item) for item in parsed]
        turns = trim_turns(turns, target_turns)
        if len(turns) < target_turns:
            raise ValueError("Model output shorter than target")
        if not is_strictly_alternating(turns):
            raise ValueError("Model output does not strictly alternate or start with ai")
        if turns[-1].role != "ai":
            raise ValueError("Final turn is not an AI recap")
        return turns

    raw_content = await request_script(strict=False)
    try:
        turns = validate_or_raise(raw_content)
    except Exception:
        raw_content = await request_script(strict=True)
        try:
            turns = validate_or_raise(raw_content)
        except Exception as exc:
            snippet = raw_content[:200].replace("\n", " ")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate a valid script. Output snippet: {snippet}",
            ) from exc

    ai_voice = os.getenv("OPENAI_TTS_VOICE_AI", "alloy")
    user_voice = os.getenv("OPENAI_TTS_VOICE_USER", "nova")
    key_prefix = f"scripts/{user_id}/{scenario_name}"
    audio_concurrency = int(os.getenv("AUDIO_GEN_CONCURRENCY", "4"))
    semaphore = asyncio.Semaphore(audio_concurrency)

    async def build_turn(index: int, turn: AIGeneratedTurns) -> Turn:
        voice = ai_voice if turn.role == "ai" else user_voice
        async with semaphore:
            audio_url = await generate_audio_url(
                client=client,
                text=turn.text,
                voice=voice,
                key_prefix=key_prefix,
            )
        return Turn(
            index=index,
            role=turn.role,
            text=turn.text,
            model_audio_url=audio_url,
        )

    script_turns = await asyncio.gather(
        *[build_turn(i, turn) for i, turn in enumerate(turns)]
    )

    return FluencyScript(totalNumberOfTurns=len(script_turns), turns=script_turns)
