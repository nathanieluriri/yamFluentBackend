from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from controller.grading.text_align import (
    AlignmentResult,
    edit_distance,
    normalized_edit_distance,
)
from schemas.speech_analysis import (
    ASRMeta,
    AlignmentMeta,
    AlignmentSummary,
    AlignedPair,
    IgnoredDifference,
    MispronouncedLogicMeta,
    MispronouncedWord,
    Token,
    TokenizationMeta,
    TurnSpeechAnalysis,
)


def _classify_op(expected: str, actual: str) -> str:
    if expected and actual:
        return "match" if expected == actual else "substitute"
    if expected and not actual:
        return "delete"
    if actual and not expected:
        return "insert"
    return "match"


def build_speech_analysis(
    *,
    expected_text: str,
    asr_text: str,
    expected_tokens: List[str],
    actual_tokens: List[str],
    alignment: AlignmentResult,
    mispronounced_words: List[str],
    threshold: float,
    asr_model: Optional[str] = None,
    asr_parameters: Optional[Dict[str, Any]] = None,
) -> TurnSpeechAnalysis:
    asr_meta = ASRMeta(
        model=asr_model,
        parameters=asr_parameters or {},
    )

    tokenization_meta = TokenizationMeta()
    alignment_meta = AlignmentMeta(threshold=threshold)
    mispronounced_meta = MispronouncedLogicMeta(
        threshold=threshold, dedupe=True, ignore_insertions=True, ignore_deletions=True
    )

    expected_token_models = [Token(idx=i, text=t) for i, t in enumerate(expected_tokens)]
    actual_token_models = [Token(idx=i, text=t) for i, t in enumerate(actual_tokens)]

    aligned_pairs: List[AlignedPair] = []
    ignored_differences: List[IgnoredDifference] = []
    mispronounced_entries: List[MispronouncedWord] = []

    seen_mispronounced: Set[str] = set()
    exp_cursor = -1
    act_cursor = -1

    for expected_word, actual_word in alignment.aligned_pairs:
        expected_idx = None
        actual_idx = None
        if expected_word:
            exp_cursor += 1
            expected_idx = exp_cursor
        if actual_word:
            act_cursor += 1
            actual_idx = act_cursor

        op = _classify_op(expected_word, actual_word)
        norm_ed = normalized_edit_distance(expected_word, actual_word)
        ed = edit_distance(expected_word, actual_word)

        aligned_pairs.append(
            AlignedPair(
                op=op,
                expected_idx=expected_idx,
                actual_idx=actual_idx,
                expected=expected_word,
                actual=actual_word,
                edit_distance=ed,
                normalized_edit_distance=norm_ed,
            )
        )

        if op == "insert":
            ignored_differences.append(
                IgnoredDifference(
                    op="insert",
                    ignored_because="insertion",
                    expected=expected_word,
                    actual=actual_word,
                    expected_idx=expected_idx,
                    actual_idx=actual_idx,
                    normalized_edit_distance=norm_ed,
                )
            )
            continue
        if op == "delete":
            ignored_differences.append(
                IgnoredDifference(
                    op="delete",
                    ignored_because="deletion",
                    expected=expected_word,
                    actual=actual_word,
                    expected_idx=expected_idx,
                    actual_idx=actual_idx,
                    normalized_edit_distance=norm_ed,
                )
            )
            continue
        if op == "match":
            ignored_differences.append(
                IgnoredDifference(
                    op="match",
                    ignored_because="exact_match",
                    expected=expected_word,
                    actual=actual_word,
                    expected_idx=expected_idx,
                    actual_idx=actual_idx,
                    normalized_edit_distance=norm_ed,
                )
            )
            continue

        if norm_ed <= threshold:
            if expected_word not in seen_mispronounced:
                seen_mispronounced.add(expected_word)
                mispronounced_entries.append(
                    MispronouncedWord(
                        expected=expected_word,
                        actual=actual_word,
                        expected_idx=expected_idx,
                        actual_idx=actual_idx,
                        normalized_edit_distance=norm_ed,
                        reason="near_miss",
                        deduped=False,
                    )
                )
            else:
                ignored_differences.append(
                    IgnoredDifference(
                        op="substitute",
                        ignored_because="deduped",
                        expected=expected_word,
                        actual=actual_word,
                        expected_idx=expected_idx,
                        actual_idx=actual_idx,
                        normalized_edit_distance=norm_ed,
                    )
                )
        else:
            ignored_differences.append(
                IgnoredDifference(
                    op="substitute",
                    ignored_because="too_far_from_expected",
                    expected=expected_word,
                    actual=actual_word,
                    expected_idx=expected_idx,
                    actual_idx=actual_idx,
                    normalized_edit_distance=norm_ed,
                )
            )

    expected_order_map = {word: i for i, word in enumerate(mispronounced_words)}
    mispronounced_entries.sort(
        key=lambda m: expected_order_map.get(m.expected, m.expected_idx or 0)
    )

    correct = max(0, len(expected_tokens) - alignment.substitutions - alignment.deletions)
    wer = (alignment.substitutions + alignment.insertions + alignment.deletions) / max(
        1, len(expected_tokens)
    )
    alignment_summary = AlignmentSummary(
        substitutions=alignment.substitutions,
        insertions=alignment.insertions,
        deletions=alignment.deletions,
        correct=correct,
        wer=wer,
    )

    return TurnSpeechAnalysis(
        expected_text=expected_text,
        asr_text=asr_text,
        asr_meta=asr_meta,
        tokenization_meta=tokenization_meta,
        alignment_meta=alignment_meta,
        mispronounced_logic_meta=mispronounced_meta,
        expected_tokens=expected_token_models,
        actual_tokens=actual_token_models,
        aligned_pairs=aligned_pairs,
        alignment_summary=alignment_summary,
        mispronounced_words=mispronounced_entries,
        ignored_differences=ignored_differences,
        extra={},
    )
