import asyncio
import json
from types import SimpleNamespace

import controller.script_generation.generate as generate
from schemas.imports import FluencyScript, ScenarioName, Turn, TurnScore
from schemas.session import SessionOut

USER_ID = "64b000000000000000000001"


def _script_reply(turns: int = 11) -> str:
    lines = [
        {"role": "ai" if i % 2 == 0 else "user", "text": f"Line {i}."} for i in range(turns)
    ]
    return json.dumps({"turns": lines})


def _past_session() -> SessionOut:
    turns = [
        Turn(index=0, role="ai", text="Tell me about your experience."),
        Turn(
            index=1,
            role="user",
            text="I have five years experience.",
            score=TurnScore(confidence=86, fluency=80, hesitation=100),
            mispronounced_words=["experience"],
        ),
        Turn(index=2, role="ai", text="Good. (Say: 'I have five years of experience.')"),
    ]
    return SessionOut(
        scenario=ScenarioName.JOB_INTERVIEW,
        userId=USER_ID,
        script=FluencyScript(totalNumberOfTurns=len(turns), turns=turns),
        date_created=100,
        last_updated=200,
    )


def _generate(monkeypatch, history):
    seen = {"prefixes": set()}

    async def fake_get_user(filter_dict):
        return SimpleNamespace(
            firstName="Tolu",
            lastName="Adeyemi",
            userPersonalProfilingData=SimpleNamespace(
                nativeLanguage="Yoruba",
                currentProficiency="INTERMEDIATE",
                mainGoals=["Reduce Hesitation"],
                learnerType="Speaking-first learner",
                dailyPracticeTime="5 mins",
            ),
        )

    async def fake_previous_sessions(user_id, scenario_name):
        seen["history_for"] = scenario_name
        return history

    async def fake_create(**kwargs):
        seen["system"], seen["user"] = (m["content"] for m in kwargs["messages"])
        message = SimpleNamespace(content=_script_reply())
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    async def fake_audio(client, text, voice, key_prefix):
        seen["prefixes"].add(key_prefix)
        return "https://audio.example/line.mp3"

    async def no_wait():
        return None

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    monkeypatch.setattr(generate, "get_user", fake_get_user)
    monkeypatch.setattr(generate, "previous_sessions", fake_previous_sessions)
    monkeypatch.setattr(generate, "get_openai_client", lambda: client)
    monkeypatch.setattr(generate, "apply_openai_rate_limit", no_wait)
    monkeypatch.setattr(generate, "generate_audio_url", fake_audio)
    script = asyncio.run(
        generate.generate_script(user_id=USER_ID, scenario_name=ScenarioName.JOB_INTERVIEW)
    )
    return script, seen


def test_scenario_enum_reaches_the_prompt_as_its_value(monkeypatch):
    script, seen = _generate(monkeypatch, history=[])
    assert script.totalNumberOfTurns == 11
    assert "Scenario: job_interview." in seen["user"]
    assert "ScenarioName" not in seen["system"] + seen["user"]
    assert seen["prefixes"] == {f"scripts/{USER_ID}/job_interview"}
    assert seen["history_for"] == "job_interview"
    assert "memory of prior practice" not in seen["system"]


def test_earlier_sessions_feed_the_memory_prompt(monkeypatch):
    _, seen = _generate(monkeypatch, history=[_past_session()])
    assert "memory of prior practice" in seen["system"]
    assert "experience" in seen["system"]
    assert "Insights:" in seen["user"]
