from controller.script_generation.prompts import (
    ScriptConfig,
    build_system_prompt_with_memory,
    extract_session_insights,
)
from schemas.imports import FluencyScript, ScenarioName, Turn, TurnScore
from schemas.session import SessionOut


def _make_session(
    last_updated: int,
    user_texts: list[str],
    ai_corrections: list[str],
    hesitations: list[int],
    mispronounced_lists: list[list[str]],
    confidence: int,
    fluency: int,
) -> SessionOut:
    turns: list[Turn] = [Turn(index=0, role="ai", text="Hi there, ready to practice?")]
    index = 0
    for user_text, ai_text, hesitation, mis_words in zip(
        user_texts, ai_corrections, hesitations, mispronounced_lists
    ):
        index += 1
        turns.append(
            Turn(
                index=index,
                role="user",
                text=user_text,
                score=TurnScore(confidence=confidence, fluency=fluency, hesitation=hesitation),
                mispronounced_words=mis_words,
            )
        )
        index += 1
        turns.append(Turn(index=index, role="ai", text=ai_text))
    script = FluencyScript(totalNumberOfTurns=len(turns), turns=turns)
    return SessionOut(
        scenario=ScenarioName.CAFE_ORDERING,
        userId="user-1",
        script=script,
        date_created=last_updated - 100,
        last_updated=last_updated,
    )


def _build_fixture_sessions() -> list[SessionOut]:
    session_one = _make_session(
        last_updated=1000,
        user_texts=["I want espresso.", "I want a mojito."],
        ai_corrections=[
            "Nice. (Say: 'I'd like an espresso, please.')",
            "Great. (Say: 'I'd like a mojito, please.')",
        ],
        hesitations=[4, 3],
        mispronounced_lists=[["espresso", "croissant"], ["mojito"]],
        confidence=2,
        fluency=2,
    )
    session_two = _make_session(
        last_updated=2000,
        user_texts=["I want espresso.", "I want a mojito."],
        ai_corrections=[
            "Good. (Say: 'I'd like an espresso, please.')",
            "Thanks. (Say: 'I'd like a mojito, please.')",
        ],
        hesitations=[2, 1],
        mispronounced_lists=[["espresso", "latte"], ["mojito"]],
        confidence=4,
        fluency=4,
    )
    return [session_one, session_two]


def test_extract_session_insights_stable_results():
    sessions = _build_fixture_sessions()
    insights = extract_session_insights(sessions)
    assert insights["total_count"] == 2
    assert insights["completed_count"] == 2
    assert insights["last_session_date"] == 2000
    assert insights["recent_average_score_trend"] == "up"
    assert "espresso" in insights["pronunciation_targets_history"]
    assert "mojito" in insights["pronunciation_targets_history"]
    assert insights["preferred_pace"] == "short"
    assert any("I want espresso." in item for item in insights["recurring_user_errors"])


def test_build_system_prompt_with_memory_constraints():
    sessions = _build_fixture_sessions()
    insights = extract_session_insights(sessions)
    config = ScriptConfig(
        user_name="Alex",
        coach_name="Maya",
        locale="en-US",
        native_language="Spanish",
        interests=["coffee"],
        daily_practice_time="5 min",
        target_turns=11,
        scenario_name="cafe_ordering",
        scenario_context="ordering at a cafe with a spicy preference",
        main_goals=["Travel"],
        learner_type="SpeakingFirstLearner",
        proficiency="BEGINNER",
        end_state="order placed and confirmed + polite closing",
    )
    prompt = build_system_prompt_with_memory(config, insights)
    assert "Output JSON ONLY" in prompt
    assert f"Total turns: {config.target_turns}" in prompt
    assert "EXACT" in prompt
    assert "Good to see you again" in prompt
    assert "TurnSpeechAnalysis" in prompt
