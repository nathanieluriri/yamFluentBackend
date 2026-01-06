from typing import Iterable, List, Set, Tuple

from controller.grading.text_align import (
    AlignmentResult,
    align_words,
    normalized_edit_distance,
)


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, value))


def clamp_leniency(leniency: float) -> float:
    return max(0.5, min(1.5, leniency))


def count_fillers(tokens: List[str]) -> Tuple[int, int]:
    filler_words: Set[str] = {"um", "uh", "uhm", "umm", "erm", "hmm", "like"}
    filler_count = 0
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in filler_words:
            filler_count += 1
            i += 1
            continue
        if token == "you" and i + 1 < len(tokens) and tokens[i + 1] == "know":
            filler_count += 1
            i += 2
            continue
        i += 1
    return filler_count, len(tokens)


def build_mispronounced_words(
    alignment: AlignmentResult,
) -> List[str]:
    mispronounced: List[str] = []
    seen = set()
    for expected_word, actual_word in alignment.aligned_pairs:
        if not expected_word or not actual_word:
            continue
        if expected_word == actual_word:
            continue
        if normalized_edit_distance(expected_word, actual_word) <= 0.4:
            if expected_word not in seen:
                seen.add(expected_word)
                mispronounced.append(expected_word)
    return mispronounced


def compute_scores(
    expected_tokens: List[str],
    actual_tokens: List[str],
    leniency: float,
) -> Tuple[int, int, int, float, int, int, AlignmentResult, List[str]]:
    strictness = 1 / clamp_leniency(leniency)
    filler_count, total_tokens = count_fillers(actual_tokens)
    filler_ratio = filler_count / max(1, total_tokens)
    alignment = align_words(expected_tokens, actual_tokens)
    wer = (alignment.substitutions + alignment.insertions + alignment.deletions) / max(
        1, len(expected_tokens)
    )
    mispronounced_words = build_mispronounced_words(alignment)
    mispronounced_ratio = len(mispronounced_words) / max(1, len(expected_tokens))

    hesitation = clamp(round(100 - (filler_ratio * 140 * strictness)))
    confidence = clamp(round(100 - (wer * 110 * strictness)))
    fluency = clamp(
        round(
            100
            - (filler_ratio * 80 * strictness)
            - (mispronounced_ratio * 120 * strictness)
            - (wer * 40 * strictness)
        )
    )

    return (
        confidence,
        fluency,
        hesitation,
        wer,
        filler_count,
        total_tokens,
        alignment,
        mispronounced_words,
    )
