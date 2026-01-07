from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    start: Optional[float] = None
    end: Optional[float] = None


class Token(BaseModel):
    idx: int
    text: str
    confidence: Optional[float] = None
    timing: Optional[WordTiming] = None


class ASRMeta(BaseModel):
    model: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    raw_response: Optional[Dict[str, Any]] = None


class TokenizationMeta(BaseModel):
    lowercase: bool = True
    strip_punctuation: bool = True
    split_on_whitespace: bool = True
    extra: Dict[str, Any] = Field(default_factory=dict)


class AlignmentMeta(BaseModel):
    algorithm: str = "edit_distance"
    ignore_insertions: bool = True
    ignore_deletions: bool = True
    threshold: float = 0.4
    extra: Dict[str, Any] = Field(default_factory=dict)


class MispronouncedLogicMeta(BaseModel):
    threshold: float = 0.4
    dedupe: bool = True
    ignore_insertions: bool = True
    ignore_deletions: bool = True
    extra: Dict[str, Any] = Field(default_factory=dict)


class AlignedPair(BaseModel):
    op: Literal["match", "substitute", "insert", "delete"]
    expected_idx: Optional[int]
    actual_idx: Optional[int]
    expected: str
    actual: str
    edit_distance: int
    normalized_edit_distance: float


class AlignmentSummary(BaseModel):
    substitutions: int
    insertions: int
    deletions: int
    correct: int
    wer: float


class MispronouncedWord(BaseModel):
    expected: str
    actual: str
    expected_idx: Optional[int]
    actual_idx: Optional[int]
    normalized_edit_distance: float
    reason: Literal["near_miss", "deduped"]
    timing: Optional[WordTiming] = None
    deduped: bool = False


class IgnoredDifference(BaseModel):
    op: Literal["match", "substitute", "insert", "delete"]
    ignored_because: Literal[
        "insertion",
        "deletion",
        "too_far_from_expected",
        "exact_match",
        "empty_side",
        "deduped",
    ]
    expected: str
    actual: str
    expected_idx: Optional[int]
    actual_idx: Optional[int]
    normalized_edit_distance: Optional[float] = None


class TurnSpeechAnalysis(BaseModel):
    expected_text: str
    asr_text: str
    asr_meta: ASRMeta
    tokenization_meta: TokenizationMeta
    alignment_meta: AlignmentMeta
    mispronounced_logic_meta: MispronouncedLogicMeta
    expected_tokens: List[Token]
    actual_tokens: List[Token]
    aligned_pairs: List[AlignedPair]
    alignment_summary: AlignmentSummary
    mispronounced_words: List[MispronouncedWord]
    ignored_differences: List[IgnoredDifference]
    extra: Dict[str, Any] = Field(default_factory=dict)
