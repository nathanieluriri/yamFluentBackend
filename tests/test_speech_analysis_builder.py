import math

from controller.grading.speech_analysis_builder import build_speech_analysis
from controller.grading.scoring import MISPRONOUNCED_THRESHOLD
from controller.grading.text_align import align_words, tokenize


def test_build_speech_analysis_near_miss():
    expected_text = "I like coffee"
    asr_text = "i like cofee"
    expected_tokens = tokenize(expected_text)
    actual_tokens = tokenize(asr_text)
    alignment = align_words(expected_tokens, actual_tokens)
    analysis = build_speech_analysis(
        expected_text=expected_text,
        asr_text=asr_text,
        expected_tokens=expected_tokens,
        actual_tokens=actual_tokens,
        alignment=alignment,
        mispronounced_words=["coffee"],
        threshold=MISPRONOUNCED_THRESHOLD,
        asr_model="test-model",
        asr_parameters={},
    )

    assert analysis.mispronounced_words, "mispronounced words should be captured"
    assert analysis.mispronounced_words[0].expected == "coffee"
    assert analysis.alignment_summary.substitutions == 1
    assert analysis.alignment_summary.insertions == 0
    assert analysis.alignment_summary.deletions == 0
    assert math.isclose(analysis.alignment_summary.wer, 1 / 3, rel_tol=1e-5)
    # matches should be logged as ignored differences
    ignored_reasons = {item.ignored_because for item in analysis.ignored_differences}
    assert "exact_match" in ignored_reasons
