from controller.script_generation.prompts import (
    ScriptConfig,
    build_system_prompt,
    normalize_learner_type,
    normalize_proficiency,
    turn_count_for_time,
)


def test_normalize_proficiency_variants():
    assert normalize_proficiency("A1") == "BEGINNER"
    assert normalize_proficiency("b2") == "INTERMEDIATE"
    assert normalize_proficiency("C2") == "ADVANCED"
    assert normalize_proficiency("beginner") == "BEGINNER"


def test_turn_count_for_time_variants():
    assert turn_count_for_time("5 min") == 11
    assert turn_count_for_time("5mins") == 11
    assert turn_count_for_time("05 mins") == 11
    assert turn_count_for_time("10 minutes") == 21


def test_normalize_learner_type_variants():
    assert normalize_learner_type("speaking first") == "SpeakingFirstLearner"
    assert normalize_learner_type("short burst") == "ShortBurstLearner"


def test_build_system_prompt_constraints_and_turns():
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
    prompt = build_system_prompt(config)
    assert "Output JSON ONLY" in prompt
    assert f"Total turns: {config.target_turns}" in prompt
    assert "AI recap" in prompt
    assert "strictly alternate" in prompt
