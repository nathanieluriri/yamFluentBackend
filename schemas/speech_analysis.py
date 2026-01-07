from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    start: Optional[float] = Field(default=None, serialization_alias="start")
    end: Optional[float] = Field(default=None, serialization_alias="end")


class Token(BaseModel):
    idx: int = Field(serialization_alias="idx")
    text: str = Field(serialization_alias="text")
    confidence: Optional[float] = Field(default=None, serialization_alias="confidence")
    timing: Optional[WordTiming] = Field(default=None, serialization_alias="timing")


class ASRMeta(BaseModel):
    model: Optional[str] = Field(default=None, serialization_alias="model")
    parameters: Dict[str, Any] = Field(default_factory=dict, serialization_alias="parameters")
    raw_response: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="rawResponse")


class TokenizationMeta(BaseModel):
    lowercase: bool = Field(default=True, serialization_alias="lowercase")
    strip_punctuation: bool = Field(default=True, serialization_alias="stripPunctuation")
    split_on_whitespace: bool = Field(default=True, serialization_alias="splitOnWhitespace")
    extra: Dict[str, Any] = Field(default_factory=dict, serialization_alias="extra")


class AlignmentMeta(BaseModel):
    algorithm: str = Field(default="edit_distance", serialization_alias="algorithm")
    ignore_insertions: bool = Field(default=True, serialization_alias="ignoreInsertions")
    ignore_deletions: bool = Field(default=True, serialization_alias="ignoreDeletions")
    threshold: float = Field(default=0.4, serialization_alias="threshold")
    extra: Dict[str, Any] = Field(default_factory=dict, serialization_alias="extra")


class MispronouncedLogicMeta(BaseModel):
    threshold: float = Field(default=0.4, serialization_alias="threshold")
    dedupe: bool = Field(default=True, serialization_alias="dedupe")
    ignore_insertions: bool = Field(default=True, serialization_alias="ignoreInsertions")
    ignore_deletions: bool = Field(default=True, serialization_alias="ignoreDeletions")
    extra: Dict[str, Any] = Field(default_factory=dict, serialization_alias="extra")


class AlignedPair(BaseModel):
    op: Literal["match", "substitute", "insert", "delete"]
    expected_idx: Optional[int] = Field(default=None, serialization_alias="expectedIdx")
    actual_idx: Optional[int] = Field(default=None, serialization_alias="actualIdx")
    expected: str = Field(serialization_alias="expected")
    actual: str = Field(serialization_alias="actual")
    edit_distance: int = Field(serialization_alias="editDistance")
    normalized_edit_distance: float = Field(serialization_alias="normalizedEditDistance")


class AlignmentSummary(BaseModel):
    substitutions: int = Field(serialization_alias="substitutions")
    insertions: int = Field(serialization_alias="insertions")
    deletions: int = Field(serialization_alias="deletions")
    correct: int = Field(serialization_alias="correct")
    wer: float = Field(serialization_alias="wer")


class MispronouncedWord(BaseModel):
    expected: str = Field(serialization_alias="expected")
    actual: str = Field(serialization_alias="actual")
    expected_idx: Optional[int] = Field(default=None, serialization_alias="expectedIdx")
    actual_idx: Optional[int] = Field(default=None, serialization_alias="actualIdx")
    normalized_edit_distance: float = Field(serialization_alias="normalizedEditDistance")
    reason: Literal["near_miss", "deduped"] = Field(serialization_alias="reason")
    timing: Optional[WordTiming] = Field(default=None, serialization_alias="timing")
    deduped: bool = Field(default=False, serialization_alias="deduped")


class IgnoredDifference(BaseModel):
    op: Literal["match", "substitute", "insert", "delete"]
    ignored_because: Literal[
        "insertion",
        "deletion",
        "too_far_from_expected",
        "exact_match",
        "empty_side",
        "deduped",
    ] = Field(serialization_alias="ignoredBecause")
    expected: str = Field(serialization_alias="expected")
    actual: str = Field(serialization_alias="actual")
    expected_idx: Optional[int] = Field(default=None, serialization_alias="expectedIdx")
    actual_idx: Optional[int] = Field(default=None, serialization_alias="actualIdx")
    normalized_edit_distance: Optional[float] = Field(default=None, serialization_alias="normalizedEditDistance")


class TurnSpeechAnalysis(BaseModel):
    expected_text: str = Field(serialization_alias="expectedText")
    asr_text: str = Field(serialization_alias="asrText")
    asr_meta: ASRMeta = Field(serialization_alias="asrMeta")
    tokenization_meta: TokenizationMeta = Field(serialization_alias="tokenizationMeta")
    alignment_meta: AlignmentMeta = Field(serialization_alias="alignmentMeta")
    mispronounced_logic_meta: MispronouncedLogicMeta = Field(serialization_alias="mispronouncedLogicMeta")
    expected_tokens: List[Token] = Field(serialization_alias="expectedTokens")
    actual_tokens: List[Token] = Field(serialization_alias="actualTokens")
    aligned_pairs: List[AlignedPair] = Field(serialization_alias="alignedPairs")
    alignment_summary: AlignmentSummary = Field(serialization_alias="alignmentSummary")
    mispronounced_words: List[MispronouncedWord] = Field(serialization_alias="mispronouncedWords")
    ignored_differences: List[IgnoredDifference] = Field(serialization_alias="ignoredDifferences")
    extra: Dict[str, Any] = Field(default_factory=dict, serialization_alias="extra")

    model_config = {
        "populate_by_name": True,
    }
