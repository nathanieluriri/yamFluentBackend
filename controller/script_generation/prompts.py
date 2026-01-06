from typing import List


def enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def normalize_proficiency(value: str) -> str:
    upper = value.upper()
    for label in ("BEGINNER", "INTERMEDIATE", "ADVANCED"):
        if label in upper:
            return label
    return value.strip()


def normalize_learner_type(value: str) -> str:
    lower = value.lower()
    if "speaking" in lower:
        return "SpeakingFirstLearner"
    if "visual" in lower:
        return "VisualLearner"
    if "short-burst" in lower or "short burst" in lower:
        return "ShortBurstLearner"
    if "structured" in lower:
        return "StructuredLearner"
    return value.strip()


def turn_count_for_time(time_value: str) -> int:
    # Deterministic mapping; odd counts ensure we can end on an AI recap turn.
    mapping = {
        "5 mins": 11,
        "10 mins": 21,
        "12 mins": 25,
        "15 mins": 31,
        "20 mins": 41,
    }
    return mapping.get(time_value, 11)


def native_language_hint(native_language: str) -> str:
    hints = {
        "Spanish (Español)": "Likely interference: article use, adjective placement, and false friends.",
        "French (Français)": "Likely interference: false friends, silent consonants, and adjective placement.",
        "Portuguese (Português)": "Likely interference: verb tense, prepositions, and false friends.",
        "German (Deutsch)": "Likely interference: word order in questions/clauses and article choice.",
        "Arabic (العربية)": "Likely interference: missing 'a/the' and /p/ vs /b/ sounds.",
        "Chinese (中文)": "Likely interference: missing articles/plurals and tense markers.",
        "Japanese (日本語)": "Likely interference: dropping subjects/articles and word order.",
        "Korean (한국어)": "Likely interference: dropping subjects/articles and tense endings.",
        "Yoruba (Yorùbá)": "Likely interference: missing articles, he/she confusion, and tense consistency.",
        "Russian (Русский)": "Likely interference: articles, word order, and aspect/tense consistency.",
        "Turkish (Türkçe)": "Likely interference: word order and prepositions.",
        "Vietnamese (Tiếng Việt)": "Likely interference: missing articles/plurals and tense markers.",
    }
    return hints.get(
        native_language,
        "Likely interference: articles, tense consistency, and word order. Keep corrections brief.",
    )


def goal_guidance(goals: List[str], scenario_name: str) -> str:
    goal_map = {
        "Travel": "Focus on practical travel interactions (check-in, directions, booking changes).",
        "Business": "Use meeting/call/email etiquette, polite requests, and negotiation language.",
        "Academic": "Practice classroom discussion, presentation transitions, and Q&A handling.",
        "Everyday Conversations": "Use casual small talk, daily errands, and routine tasks.",
        "Sound More Polite": "Offer polite alternatives, softeners, and respectful phrasing.",
        "Sound Clearer": "Favor short, clear sentences with explicit subjects and transitions.",
        "Reduce Hesitation": "Use quick-response prompts and encourage fillers like 'well' or 'let me think'.",
        "Improve Pronunciation": "Add brief pronunciation tips in AI turns (text-only, no IPA overload).",
        "Succeed in Job Interviews": "Follow interview Q/A structure with follow-up questions.",
        "Sound More Natural": "Include idioms/collocations and more natural responses.",
        "Stop Translating in My Head": "Encourage thinking in the target language; avoid translations.",
    }
    guidance = [goal_map.get(goal, goal) for goal in goals]
    scenario_line = f"Scenario focus: {scenario_name}."
    return " ".join([scenario_line] + guidance)


def learner_type_guidance(learner_type: str) -> str:
    if learner_type == "SpeakingFirstLearner":
        return "Keep AI prompts short and question-heavy; prioritize learner speaking time."
    if learner_type == "VisualLearner":
        return "Include example answers and clear patterns; use bullet-like formatting in text."
    if learner_type == "ShortBurstLearner":
        return "Use micro-drills and quick back-and-forth; minimize exposition."
    if learner_type == "StructuredLearner":
        return "Follow a step-by-step flow: warm-up, model, guided practice, free practice, recap."
    return "Balance guidance and practice turns."


def proficiency_guidance(level: str) -> str:
    if level == "BEGINNER":
        return "Use simple vocab and short sentences; add scaffolding and occasional options."
    if level == "INTERMEDIATE":
        return "Use natural but accessible phrasing with moderate complexity."
    if level == "ADVANCED":
        return "Use nuanced language, idioms, and complex follow-ups with minimal scaffolding."
    return "Adapt complexity appropriately."


def build_system_prompt(
    target_turns: int,
    goals: List[str],
    learner_type: str,
    proficiency: str,
    native_language: str,
    scenario_name: str,
) -> str:
    return (
        "You are a language coaching AI. Output JSON ONLY: a list of objects with keys "
        "'role' (ai|user) and 'text'. No markdown. Start with role='ai' and strictly alternate "
        "roles. End with a final AI recap that summarizes corrections and gives 2-3 takeaways "
        "aligned with goals. The user turns are expected learner responses/prompts and must not be blank. "
        f"Total turns: {target_turns}. "
        f"{goal_guidance(goals, scenario_name)} "
        f"{learner_type_guidance(learner_type)} "
        f"{proficiency_guidance(proficiency)} "
        f"Native language note: {native_language_hint(native_language)} "
        "Avoid long translations; if needed, use only single-word clarifications."
    )


def build_user_prompt(
    scenario_name: str,
    goals: List[str],
    daily_practice_time: str,
) -> str:
    goals_text = ", ".join(goals) if goals else "No specific goals provided"
    return (
        f"Scenario: {scenario_name}. Daily practice time: {daily_practice_time}. "
        f"Main goals: {goals_text}. "
        "Generate the full script now."
    )
