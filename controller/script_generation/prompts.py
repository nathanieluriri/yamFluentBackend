from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


def enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def normalize_proficiency(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "BEGINNER"
    upper = raw.upper()
    condensed = re.sub(r"[^A-Z0-9]+", "", upper)
    if condensed in {"A1", "A2"} or "BEGINNER" in upper:
        return "BEGINNER"
    if condensed in {"B1", "B2"} or "INTERMEDIATE" in upper:
        return "INTERMEDIATE"
    if condensed in {"C1", "C2"} or "ADVANCED" in upper:
        return "ADVANCED"
    return raw.strip()


def normalize_learner_type(value: str) -> str:
    lower = (value or "").strip().lower()
    if "speaking" in lower or "speaking-first" in lower or "speaking first" in lower:
        return "SpeakingFirstLearner"
    if "visual" in lower:
        return "VisualLearner"
    if "short-burst" in lower or "short burst" in lower or "shortburst" in lower:
        return "ShortBurstLearner"
    if "structured" in lower:
        return "StructuredLearner"
    return (value or "").strip()


def normalize_time_value(time_value: str) -> int:
    if not time_value:
        return 0
    match = re.search(r"(\d+)", time_value.lower())
    if not match:
        return 0
    return int(match.group(1))


def turn_count_for_time(time_value: str) -> int:
    mapping = {
        5: 11,
        10: 21,
        12: 25,
        15: 31,
        20: 41,
    }
    minutes = normalize_time_value(time_value)
    return mapping.get(minutes, 11)


def _normalize_scenario_key(scenario_name: str) -> str:
    if not scenario_name:
        return ""
    return re.sub(r"\s+", "_", scenario_name.strip().lower())


def default_scenario_context(scenario_name: str) -> str:
    scenario_key = _normalize_scenario_key(scenario_name)
    contexts = {
        "cafe_ordering": "You are ordering at a cafe and prefer spicy flavors.",
        "airport_check_in": "You are checking in for a flight with one checked bag.",
        "doctor_visit": "You are visiting a doctor to discuss symptoms and get advice.",
        "job_interview": "You are interviewing and highlighting relevant experience.",
        "school_class_participation": "You are in class and want to answer and ask a question.",
        "school_presentation": "You are giving a short presentation and taking questions.",
        "school_enrollment": "You are enrolling and clarifying required documents.",
        "university_orientation": "You are at orientation asking about schedules and locations.",
        "university_seminar_discussion": "You are in a seminar discussing a reading and sharing a view.",
        "university_admin_office": "You are resolving a registration issue at the admin office.",
        "group_project_meeting": "You are assigning tasks and deadlines with teammates.",
        "dorm_roommate_discussion": "You are discussing shared rules with a roommate.",
        "library_research_help": "You are asking a librarian for sources on a topic.",
        "campus_club_meeting": "You are introducing yourself at a club and volunteering.",
        "workplace_team_meeting": "You are giving a status update and aligning priorities.",
        "customer_support_call": "You are calling support to fix a product issue.",
        "apartment_rental_viewing": "You are viewing an apartment and asking about terms.",
        "bank_account_opening": "You are opening a bank account and confirming requirements.",
    }
    return contexts.get(scenario_key, "You are practicing a realistic conversation.")


def default_end_state(scenario_name: str) -> str:
    scenario_key = _normalize_scenario_key(scenario_name)
    end_states = {
        "cafe_ordering": "order placed and confirmed + polite closing",
        "airport_check_in": "checked in, baggage handled, and boarding pass confirmed",
        "doctor_visit": "symptoms explained, advice understood, and next step confirmed",
        "job_interview": "strengths shared and next steps clarified",
        "school_class_participation": "question answered and follow-up asked",
        "school_presentation": "presentation delivered and questions handled",
        "school_enrollment": "requirements confirmed and next step agreed",
        "university_orientation": "key locations clarified and schedule confirmed",
        "university_seminar_discussion": "main point stated and discussion advanced",
        "university_admin_office": "issue clarified and resolution path agreed",
        "group_project_meeting": "tasks assigned and deadlines confirmed",
        "dorm_roommate_discussion": "rules agreed and polite closing",
        "library_research_help": "sources identified and next step confirmed",
        "campus_club_meeting": "introduction done and participation agreed",
        "workplace_team_meeting": "update delivered and next actions aligned",
        "customer_support_call": "issue described and fix confirmed",
        "apartment_rental_viewing": "questions answered and viewing wrapped up",
        "bank_account_opening": "requirements confirmed and account opened",
    }
    return end_states.get(scenario_key, "task completed and polite closing")


def native_language_interference(native_language: str) -> str:
    value = (native_language or "").strip().lower()
    if "spanish" in value:
        return "Likely interference: article use, adjective placement, and vowel length."
    if "french" in value:
        return "Likely interference: silent consonants, th sounds, and vowel pairs."
    if "arabic" in value:
        return "Likely interference: missing a/the, /p/ vs /b/, and clusters."
    if "chinese" in value:
        return "Likely interference: missing articles/plurals and tense markers."
    if "yoruba" in value:
        return "Likely interference: articles, /v/ vs /f/, and ending consonants."
    return (
        "Likely interference: articles, tense consistency, and word order. Keep corrections brief."
    )


def _language_key(native_language: str) -> str:
    value = (native_language or "").strip().lower()
    if "yoruba" in value:
        return "yoruba"
    if "spanish" in value:
        return "spanish"
    if "french" in value:
        return "french"
    if "arabic" in value:
        return "arabic"
    if "chinese" in value:
        return "chinese"
    return "generic"


def pronunciation_targets(
    native_language: str,
    scenario_name: str,
    proficiency: str,
    count: int,
) -> List[str]:
    scenario_key = _normalize_scenario_key(scenario_name)
    base_targets = {
        "yoruba": [
            ("think", "th sound"),
            ("this", "voiced th"),
            ("very", "v sound"),
            ("street", "consonant cluster str"),
            ("world", "ending consonants"),
            ("crisps", "final cluster sps"),
            ("friends", "end cluster nds"),
        ],
        "spanish": [
            ("ship", "short i vs long ee"),
            ("sheep", "long ee vs short i"),
            ("very", "v sound"),
            ("beach", "final ch"),
            ("asked", "final consonants"),
            ("street", "cluster str"),
            ("world", "ending consonants"),
        ],
        "french": [
            ("think", "th sound"),
            ("this", "voiced th"),
            ("ship", "short i"),
            ("sheep", "long ee"),
            ("world", "r and ending consonants"),
            ("street", "cluster str"),
            ("hotel", "h sound"),
        ],
        "arabic": [
            ("park", "p sound"),
            ("paper", "p sound"),
            ("very", "v sound"),
            ("baggage", "soft g"),
            ("street", "cluster str"),
            ("world", "ending consonants"),
            ("asked", "final cluster skt"),
        ],
        "chinese": [
            ("light", "l vs r"),
            ("right", "r vs l"),
            ("think", "th sound"),
            ("ship", "short i"),
            ("sheep", "long ee"),
            ("street", "cluster str"),
            ("world", "ending consonants"),
        ],
        "generic": [
            ("think", "th sound"),
            ("this", "voiced th"),
            ("world", "ending consonants"),
            ("street", "cluster str"),
            ("very", "v sound"),
            ("asked", "final cluster skt"),
        ],
    }
    scenario_targets = {
        "cafe_ordering": [
            ("croissant", "silent letters and vowel blend"),
            ("crisps", "final cluster sps"),
            ("menu", "stress on first syllable"),
        ],
        "airport_check_in": [
            ("passport", "cluster sp"),
            ("boarding", "ending consonant"),
            ("baggage", "soft g"),
            ("ac-com-mo-date", "syllable breaks and stress"),
        ],
        "doctor_visit": [
            ("symptom", "cluster mp"),
            ("prescription", "stress and consonants"),
            ("allergy", "ending y"),
        ],
        "job_interview": [
            ("strengths", "cluster ngths"),
            ("experience", "stress and vowel"),
            ("qualifications", "multi-syllable word"),
        ],
        "bank_account_opening": [
            ("deposit", "stress on second syllable"),
            ("documents", "ending consonant"),
            ("statement", "cluster st"),
        ],
    }
    targets = scenario_targets.get(scenario_key, []) + base_targets[_language_key(native_language)]
    if count <= 0:
        return []
    output: List[str] = []
    seen = set()
    for word, reason in targets:
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(f"{word} - {reason}")
        if len(output) >= count:
            break
    return output


def goal_guidance(goals: Sequence[str], scenario_name: str) -> str:
    goal_map = {
        "Travel": "Focus on practical travel interactions (check-in, directions, booking changes).",
        "Business": "Use meeting/call/email etiquette, polite requests, and negotiation language.",
        "Academic": "Practice classroom discussion, presentation transitions, and Q&A handling.",
        "Everyday Conversations": "Use casual small talk, daily errands, and routine tasks.",
        "Sound More Polite": "Offer polite alternatives, softeners, and respectful phrasing.",
        "Sound Clearer": "Favor short, clear sentences with explicit subjects and transitions.",
        "Reduce Hesitation": "Use quick-response prompts and confident, direct replies.",
        "Improve Pronunciation": "Add brief pronunciation tips in AI turns (text-only, no IPA).",
        "Succeed in Job Interviews": "Follow interview Q/A structure with follow-up questions.",
        "Sound More Natural": "Include idioms/collocations and natural responses, kept concise.",
        "Stop Translating in My Head": "Encourage thinking in the target language; avoid translations.",
    }
    guidance = [goal_map.get(goal, goal) for goal in goals]
    scenario_line = f"Scenario focus: {scenario_name}."
    return " ".join([scenario_line] + guidance)


def learner_type_guidance(learner_type: str) -> str:
    if learner_type == "SpeakingFirstLearner":
        return "Keep AI prompts short and question-heavy; prioritize learner speaking time."
    if learner_type == "VisualLearner":
        return "Include example answers and clear patterns."
    if learner_type == "ShortBurstLearner":
        return "Use micro-drills and quick back-and-forth; minimize exposition."
    if learner_type == "StructuredLearner":
        return "Follow a step-by-step flow: warm-up, model, guided practice, free practice, recap."
    return "Balance guidance and practice turns."


def proficiency_guidance(level: str) -> str:
    if level == "BEGINNER":
        return "Use simple vocab and short sentences; add scaffolding and options."
    if level == "INTERMEDIATE":
        return "Use natural but accessible phrasing with moderate complexity."
    if level == "ADVANCED":
        return "Use nuanced language, idioms, and complex follow-ups with minimal scaffolding."
    return "Adapt complexity appropriately."


def word_limits_for_proficiency(level: str) -> Tuple[int, int]:
    normalized = normalize_proficiency(level)
    if normalized == "BEGINNER":
        return 10, 18
    if normalized == "INTERMEDIATE":
        return 14, 24
    if normalized == "ADVANCED":
        return 18, 32
    return 12, 22


@dataclass
class ScriptConfig:
    user_name: str
    coach_name: str = "Coach"
    locale: str = "en-US"
    native_language: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    daily_practice_time: str = ""
    target_turns: int = 0
    scenario_name: str = ""
    scenario_context: str = ""
    main_goals: List[str] = field(default_factory=list)
    learner_type: str = ""
    proficiency: str = ""
    strict_no_filler_user: bool = True
    user_turn_max_words: int = 0
    ai_turn_max_words: int = 0
    pronunciation_focus: bool = True
    pronunciation_targets_count: int = 6
    difficulty_ramp: bool = True
    end_state: str = ""

    def __post_init__(self) -> None:
        if not self.user_name:
            raise ValueError("user_name is required")
        if not self.target_turns and self.daily_practice_time:
            self.target_turns = turn_count_for_time(self.daily_practice_time)
        if not self.target_turns:
            self.target_turns = 11
        self.learner_type = normalize_learner_type(self.learner_type)
        self.proficiency = normalize_proficiency(self.proficiency)
        if not self.scenario_context:
            self.scenario_context = default_scenario_context(self.scenario_name)
        if not self.end_state:
            self.end_state = default_end_state(self.scenario_name)
        if self.user_turn_max_words <= 0 or self.ai_turn_max_words <= 0:
            user_max, ai_max = word_limits_for_proficiency(self.proficiency)
            if self.user_turn_max_words <= 0:
                self.user_turn_max_words = user_max
            if self.ai_turn_max_words <= 0:
                self.ai_turn_max_words = ai_max


def assert_turn_plan(target_turns: int) -> str:
    if target_turns < 5:
        raise ValueError("target_turns must be at least 5 to include a recap")
    if target_turns % 2 == 0:
        raise ValueError("target_turns must be odd to end on an AI recap")
    return (
        "Turn blueprint: 1 = warm greeting + context check; "
        f"2..{target_turns - 2} = task progression + corrections + pronunciation targets; "
        f"{target_turns - 1} = confirmation + closing question; "
        f"{target_turns} = recap (no questions)."
    )


def build_fewshot_examples(config: ScriptConfig) -> str:
    user_name = config.user_name
    coach_name = config.coach_name
    example_a = [
        {
            "role": "ai",
            "text": f"Hi {user_name}, I'm {coach_name}. Ready to order at the cafe?",
        },
        {"role": "user", "text": "Hi. I want a coffee and a croissant."},
        {
            "role": "ai",
            "text": (
                "Nice. (Say: 'I'd like a coffee and a croissant, please.') "
                "Hot or iced? Say croissant like 'kroh-sahnt'."
            ),
        },
        {"role": "user", "text": "Hot, please."},
        {
            "role": "ai",
            "text": "Great. Any food, like soup or crisps? Say crisps like 'krisps'.",
        },
        {"role": "user", "text": "A small soup, please."},
        {
            "role": "ai",
            "text": (
                "Recap: Corrections - 'I'd like a coffee and a croissant, please.' "
                "Takeaways - use please, choose hot or iced. "
                "Micro-drill: Say 'I'd like a hot coffee, please' three times."
            ),
        },
    ]
    example_b = [
        {
            "role": "ai",
            "text": f"Hi {user_name}, airport check-in practice. Do you have a passport?",
        },
        {"role": "user", "text": "Yes, and one checked bag."},
        {
            "role": "ai",
            "text": (
                "Thanks. (Say: 'I have one checked bag.') "
                "Do you want aisle or window? Say aisle like 'ile'."
            ),
        },
        {"role": "user", "text": "Aisle, please."},
        {"role": "ai", "text": "Got it. Any seat near the front?"},
        {"role": "user", "text": "Yes, if possible."},
        {
            "role": "ai",
            "text": (
                "Recap: Corrections - 'I have one checked bag.' "
                "Takeaways - state bag count, request seat. "
                "Micro-drill: Say 'I have one checked bag and an aisle seat' once."
            ),
        },
    ]
    return (
        "Example A (Beginner, cafe ordering):\n"
        f"{json.dumps({'turns': example_a})}\n"
        "Example B (Intermediate, travel check-in):\n"
        f"{json.dumps({'turns': example_b})}"
    )


def build_system_prompt(config: ScriptConfig) -> str:
    plan_line = assert_turn_plan(config.target_turns)
    pronunciation_list = pronunciation_targets(
        native_language=config.native_language or "",
        scenario_name=config.scenario_name,
        proficiency=config.proficiency,
        count=config.pronunciation_targets_count,
    )
    pronunciation_text = "; ".join(pronunciation_list)
    advanced_requirement = ""
    if config.proficiency == "ADVANCED":
        advanced_requirement = (
            "ADVANCED requirement: include 6-10 rare but scenario-relevant words/phrases "
            "in AI turns, and have the user repeat 2-3 of them."
        )
    filler_rule = ""
    if config.strict_no_filler_user:
        filler_rule = (
            "User turns must not include filler words like um, well, like, you know, "
            "or let me think."
        )
    pronunciation_rule = ""
    if not config.pronunciation_focus:
        pronunciation_rule = "Pronunciation focus is off: include at most 2 targets total."
    ramp_rule = ""
    if config.difficulty_ramp:
        ramp_rule = "Increase difficulty gradually across the turns."

    lines = [
        "You are a language coaching AI.",
        (
            "Output JSON ONLY: an object with key \"turns\" that is a list of objects "
            "with keys \"role\" (ai|user) and \"text\". No markdown."
        ),
        (
            "Start with role='ai' and strictly alternate roles. "
            f"Total turns: {config.target_turns} (EXACT)."
        ),
        (
            "The last item MUST be an AI recap turn with: 2-4 corrections (very short), "
            "2-3 takeaways aligned to goals, and one micro-drill (1 sentence). "
            "Do not ask a question in the final turn."
        ),
        "User turns are plausible learner replies, concise and confident.",
        filler_rule,
        (
            "AI turns are warm, direct, and short, not lecture-like. Ask one question per "
            "AI turn max (unless offering 2-3 choices)."
        ),
        (
            "When the user makes an error, respond naturally then add a quick correction "
            "in parentheses, e.g., Nice choice. (Say: 'I'd like a virgin mojito, please.')"
        ),
        "Do not use IPA. Use 'say it like' hints and syllable breaks only when needed.",
        (
            "Pronunciation targets: inject about 1 target word every 2 user turns and model it. "
            f"Targets: {pronunciation_text}"
        ),
        (
            "Turn budget: user <= "
            f"{config.user_turn_max_words} words; ai <= {config.ai_turn_max_words} words."
        ),
        f"Personalize using user_name, coach_name, locale, interests, and scenario context.",
        f"End state: {config.end_state}.",
        goal_guidance(config.main_goals, config.scenario_name),
        learner_type_guidance(config.learner_type),
        proficiency_guidance(config.proficiency),
        native_language_interference(config.native_language or ""),
        ramp_rule,
        advanced_requirement,
        pronunciation_rule,
        plan_line,
        "Few-shot examples (style only; do not copy text):",
        build_fewshot_examples(config),
    ]
    return "\n".join([line for line in lines if line])


def build_user_prompt(config: ScriptConfig) -> str:
    goals_text = ", ".join(config.main_goals) if config.main_goals else "No specific goals"
    interests_text = ", ".join(config.interests) if config.interests else "None provided"
    native_language = config.native_language or "Not provided"
    return (
        f"User name: {config.user_name}. Coach name: {config.coach_name}. "
        f"Locale: {config.locale}. Scenario: {config.scenario_name}. "
        f"Scenario context: {config.scenario_context}. End state: {config.end_state}. "
        f"Native language: {native_language}. Interests: {interests_text}. "
        f"Main goals: {goals_text}. Learner type: {config.learner_type}. "
        f"Proficiency: {config.proficiency}. Daily practice time: {config.daily_practice_time}. "
        f"Target turns: {config.target_turns}. "
        f"Generate the full script now. Make it end in {config.target_turns} turns "
        f"and reach end_state: {config.end_state}."
    )


def _session_timestamp(session: object) -> int:
    last_updated = getattr(session, "last_updated", None)
    if last_updated:
        return int(last_updated)
    date_created = getattr(session, "date_created", None)
    if date_created:
        return int(date_created)
    return 0


def _session_total_turns(session: object) -> Optional[int]:
    script = getattr(session, "script", None)
    if not script:
        return None
    total_turns = getattr(script, "totalNumberOfTurns", None)
    if total_turns is None:
        turns = getattr(script, "turns", None)
        if turns is not None:
            total_turns = len(turns)
    return total_turns if total_turns else None


def _normalize_word(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^A-Za-z'-]+", "", value).strip().lower()
    return cleaned


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-z']+", text.lower())


def _ngrams(tokens: List[str], min_n: int = 2, max_n: int = 4) -> Set[str]:
    output: Set[str] = set()
    for n in range(min_n, max_n + 1):
        for i in range(len(tokens) - n + 1):
            output.add(" ".join(tokens[i : i + n]))
    return output


def _extract_correction_text(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(r"\(\s*Say:\s*['\"]([^'\"]+)['\"]\s*\)", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"Say:\s*['\"]([^'\"]+)['\"]", text)
    if match:
        return match.group(1).strip()
    return None


def _get_attr_or_key(value: object, key: str) -> Optional[Any]:
    if value is None:
        return None
    if hasattr(value, key):
        return getattr(value, key)
    if isinstance(value, dict):
        if key in value:
            return value.get(key)
        if "_" in key:
            parts = key.split("_")
            camel_key = parts[0] + "".join(part.capitalize() for part in parts[1:])
            return value.get(camel_key)
    return None


def extract_session_insights(previous_sessions_same_scenario: Sequence[object]) -> Dict[str, Any]:
    sessions = list(previous_sessions_same_scenario or [])
    total_count = len(sessions)
    completed_count = 0
    timestamps: List[int] = []
    score_series: List[Tuple[int, float]] = []
    hesitation_scores: List[Tuple[int, int]] = []
    word_counts: Dict[str, int] = {}
    word_sessions: Dict[str, Set[int]] = {}
    corrections: List[Tuple[str, str, int, Set[str]]] = []
    ngram_sessions: Dict[str, Set[int]] = {}
    turn_counts: List[int] = []

    for session_idx, session in enumerate(sessions):
        timestamp = _session_timestamp(session)
        if timestamp:
            timestamps.append(timestamp)
        average_score = getattr(session, "average_score", None)
        if average_score is not None:
            score_series.append((timestamp, float(average_score)))
        completed = getattr(session, "completed", None)
        if completed is None:
            script = getattr(session, "script", None)
            if script and getattr(script, "turns", None):
                completed = all(
                    getattr(turn, "score", None) is not None
                    for turn in script.turns
                    if getattr(turn, "role", None) == "user"
                )
        if completed:
            completed_count += 1

        total_turns = _session_total_turns(session)
        if total_turns:
            turn_counts.append(total_turns)

        script = getattr(session, "script", None)
        turns = list(getattr(script, "turns", None) or [])
        turns.sort(key=lambda turn: getattr(turn, "index", 0))

        for i, turn in enumerate(turns):
            if getattr(turn, "role", None) == "user":
                score = getattr(turn, "score", None)
                hesitation = getattr(score, "hesitation", None) if score else None
                if hesitation is not None:
                    hesitation_scores.append((int(hesitation), int(getattr(turn, "index", i))))

                for word in (getattr(turn, "mispronounced_words", None) or []):
                    normalized = _normalize_word(str(word))
                    if not normalized:
                        continue
                    word_counts[normalized] = word_counts.get(normalized, 0) + 1
                    word_sessions.setdefault(normalized, set()).add(session_idx)

                speech_analysis = getattr(turn, "speech_analysis", None)
                for item in (_get_attr_or_key(speech_analysis, "mispronounced_words") or []):
                    expected = _get_attr_or_key(item, "expected") or _get_attr_or_key(item, "actual")
                    normalized = _normalize_word(str(expected)) if expected else ""
                    if not normalized:
                        continue
                    word_counts[normalized] = word_counts.get(normalized, 0) + 1
                    word_sessions.setdefault(normalized, set()).add(session_idx)

            if getattr(turn, "role", None) != "user":
                continue
            next_turn = turns[i + 1] if i + 1 < len(turns) else None
            if not next_turn or getattr(next_turn, "role", None) != "ai":
                continue
            correction = _extract_correction_text(getattr(next_turn, "text", ""))
            user_text = str(getattr(turn, "text", "")).strip()
            if not correction or not user_text:
                continue
            tokens = _tokenize(user_text)
            ngrams = _ngrams(tokens)
            corrections.append((user_text, correction, session_idx, ngrams))
            for ngram in ngrams:
                ngram_sessions.setdefault(ngram, set()).add(session_idx)

    last_session_date = max(timestamps) if timestamps else None

    score_series.sort(key=lambda pair: pair[0])
    recent_scores = [score for _, score in score_series[-3:]]
    recent_average_score_trend = "flat"
    if len(recent_scores) >= 2:
        delta = recent_scores[-1] - recent_scores[0]
        if delta > 0.05:
            recent_average_score_trend = "up"
        elif delta < -0.05:
            recent_average_score_trend = "down"

    hesitation_scores.sort(key=lambda pair: (-pair[0], pair[1]))
    top_user_hesitation_turns = [index for _, index in hesitation_scores[:3]]
    average_hesitation = (
        sum(score for score, _ in hesitation_scores) / len(hesitation_scores)
        if hesitation_scores
        else None
    )
    hesitation_high = average_hesitation is not None and average_hesitation >= 3

    repeated_words = [
        word for word, sessions_set in word_sessions.items() if len(sessions_set) >= 2
    ]
    repeated_words.sort(key=lambda word: (-word_counts[word], word))
    remaining_words = [word for word in word_counts.keys() if word not in repeated_words]
    remaining_words.sort(key=lambda word: (-word_counts[word], word))
    pronunciation_targets_history = (repeated_words + remaining_words)[:6]

    repeated_ngrams = {ng for ng, sessions_set in ngram_sessions.items() if len(sessions_set) >= 2}
    scored_pairs: List[Tuple[int, str, str]] = []
    for user_text, correction, _, ngrams in corrections:
        score = sum(1 for ngram in ngrams if ngram in repeated_ngrams)
        if score > 0:
            scored_pairs.append((score, user_text, correction))

    if not scored_pairs:
        user_text_counts: Dict[str, int] = {}
        for user_text, _, _, _ in corrections:
            normalized = " ".join(_tokenize(user_text))
            user_text_counts[normalized] = user_text_counts.get(normalized, 0) + 1
        for user_text, correction, _, _ in corrections:
            normalized = " ".join(_tokenize(user_text))
            if user_text_counts.get(normalized, 0) >= 2:
                scored_pairs.append((user_text_counts[normalized], user_text, correction))

    scored_pairs.sort(key=lambda item: (-item[0], item[1].lower()))
    recurring_user_errors: List[str] = []
    seen_pairs = set()
    for _, user_text, correction in scored_pairs:
        key = (user_text.lower(), correction.lower())
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        recurring_user_errors.append(f"{user_text} -> {correction}")
        if len(recurring_user_errors) >= 6:
            break

    if turn_counts:
        avg_turns = sum(turn_counts) / len(turn_counts)
        if avg_turns <= 11:
            preferred_pace = "short"
        elif avg_turns <= 21:
            preferred_pace = "standard"
        else:
            preferred_pace = "long"
    else:
        preferred_pace = "standard"

    return {
        "has_history": total_count > 0,
        "last_session_date": last_session_date,
        "completed_count": completed_count,
        "total_count": total_count,
        "recent_average_score_trend": recent_average_score_trend,
        "top_user_hesitation_turns": top_user_hesitation_turns,
        "average_user_hesitation": average_hesitation,
        "hesitation_high": hesitation_high,
        "recurring_user_errors": recurring_user_errors,
        "pronunciation_targets_history": pronunciation_targets_history,
        "preferred_pace": preferred_pace,
    }


def build_fewshot_examples_with_memory(config: ScriptConfig) -> str:
    user_name = config.user_name
    example = [
        {
            "role": "ai",
            "text": (
                f"Good to see you again, {user_name}. "
                
            ),
        },
        {"role": "user", "text": "I want a mojito, please."},
        {
            "role": "ai",
            "text": (
                "Nice. Getting your order right up "
                
            ),
        },
        {"role": "user", "text": "Thanks, I appreciate it, could I choose the temperature also."},
        {"role": "ai", "text": "Great. Hot or iced mojito?"},
        {"role": "user", "text": "Iced, please."},
        {
            "role": "ai",
            "text": (
                "Recap: Corrections - 'I'd like a mojito, please.' "
                "Takeaways - use I'd like, answer with please. "
                "Micro-drill: Say 'I'd like an iced coffee, please' once."
            ),
        },
    ]
    return (
        "Example (memory-aware, cafe ordering):\n"
        f"{json.dumps({'turns': example})}"
    )


def build_system_prompt_with_memory(config: ScriptConfig, insights: Dict[str, Any]) -> str:
    plan_line = assert_turn_plan(config.target_turns)
    pronunciation_list = pronunciation_targets(
        native_language=config.native_language or "",
        scenario_name=config.scenario_name,
        proficiency=config.proficiency,
        count=config.pronunciation_targets_count,
    )
    pronunciation_text = "; ".join(pronunciation_list)
    history_pronunciation = ", ".join(insights.get("pronunciation_targets_history", []))
    recurring_errors = insights.get("recurring_user_errors", [])
    recurring_errors_text = " | ".join(recurring_errors)

    memory_line = (
        "If insights.has_history is true, include one short remember line early, "
        "e.g., 'Good to see you again - let's pick up where we left off.' "
        "If false, greet as first time in this scenario."
    )
    hesitation_line = ""
    if insights.get("hesitation_high"):
        hesitation_line = (
            "Hesitation was high previously; keep user turns extra short and confident."
        )

    trend_line = ""
    if config.proficiency in {"INTERMEDIATE", "ADVANCED"}:
        trend = insights.get("recent_average_score_trend")
        avg_hesitation = insights.get("average_user_hesitation")
        low_hesitation = avg_hesitation is not None and avg_hesitation <= 2
        if trend == "up" or low_hesitation:
            trend_line = "Recent performance improved; gently ramp complexity and diction."
        elif trend == "down":
            trend_line = "Recent scores dipped; keep difficulty steady and supportive."

    advanced_requirement = ""
    if config.proficiency == "ADVANCED":
        advanced_requirement = (
            "ADVANCED requirement: include 6-10 rare but scenario-relevant words/phrases "
            "in AI turns, and have the user repeat 2-3 of them."
        )

    filler_rule = ""
    if config.strict_no_filler_user:
        filler_rule = (
            "User turns must not include filler words like um, well, like, you know, "
            "or let me think."
        )

    lines = [
        "You are a language coaching AI with memory of prior practice.",
        (
            "Output JSON ONLY: an object with key \"turns\" that is a list of objects "
            "with keys \"role\" (ai|user) and \"text\". No markdown."
        ),
        (
            "Start with role='ai' and strictly alternate roles. "
            f"Total turns: {config.target_turns} (EXACT)."
        ),
        (
            "The last turn MUST be an AI recap turn with: 2-4 corrections (very short), "
            "2-3 takeaways aligned to goals, and one micro-drill (1 sentence). "
            "Do not ask a question in the final turn."
        ),
        memory_line,
        "Do not mention analytics or internal data; reference 'last time' naturally.",
        f"Memory insights (internal use only): {json.dumps(insights, separators=(',', ':'))}",
        (
            "Use TurnSpeechAnalysis-derived pronunciation targets from history; include 4-6 of these "
            f"across the script and model each briefly: {history_pronunciation}"
        ),
        (
            "Also add 1-2 new scenario-relevant pronunciation targets: "
            f"{pronunciation_text}"
        ),
        (
            "Use 2-3 recurring error pairs as practice moments (have the user produce the corrected form): "
            f"{recurring_errors_text}"
        ),
        "User turns are plausible learner replies, concise and confident.",
        filler_rule,
        (
            "AI turns are warm, direct, and short, not lecture-like. Ask one question per "
            "AI turn max (unless offering 2-3 choices)."
        ),
       
        "Do not use IPA. DO NOT Use 'say it like' or give hints and or syllable breaks.",
        (
            "Turn budget: user <= "
            f"{config.user_turn_max_words} words; ai <= {config.ai_turn_max_words} words."
        ),
        f"Personalize using user_name, coach_name, locale, interests, and scenario context.",
        f"End state: {config.end_state}.",
        goal_guidance(config.main_goals, config.scenario_name),
        learner_type_guidance(config.learner_type),
        proficiency_guidance(config.proficiency),
        native_language_interference(config.native_language or ""),
        hesitation_line,
        trend_line,
        advanced_requirement,
        plan_line,
        "Few-shot example (style only; do not copy text):",
        build_fewshot_examples_with_memory(config),
    ]
    return "\n".join([line for line in lines if line])


def build_user_prompt_with_memory(config: ScriptConfig, insights: Dict[str, Any]) -> str:
    goals_text = ", ".join(config.main_goals) if config.main_goals else "No specific goals"
    interests_text = ", ".join(config.interests) if config.interests else "None provided"
    native_language = config.native_language or "Not provided"
    insights_blob = json.dumps(insights, separators=(",", ":"), ensure_ascii=True)
    return (
        f"User name: {config.user_name}. Coach name: {config.coach_name}. "
        f"Locale: {config.locale}. Scenario: {config.scenario_name}. "
        f"Scenario context: {config.scenario_context}. End state: {config.end_state}. "
        f"Native language: {native_language}. Interests: {interests_text}. "
        f"Main goals: {goals_text}. Learner type: {config.learner_type}. "
        f"Proficiency: {config.proficiency}. Daily practice time: {config.daily_practice_time}. "
        f"Target turns: {config.target_turns}. "
        f"Insights: {insights_blob}. "
        f"Generate the full script now. Make it end in exactly {config.target_turns} turns "
        f"and reach end_state: {config.end_state}."
    )
