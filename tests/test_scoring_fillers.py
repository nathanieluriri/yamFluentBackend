from controller.grading.scoring import compute_scores, count_fillers
from controller.grading.text_align import tokenize


def _scores(expected: str, said: str):
    confidence, fluency, hesitation, wer, fillers, total, _, _ = compute_scores(
        tokenize(expected), tokenize(said), leniency=1.0
    )
    return confidence, fluency, hesitation, fillers


def test_scripted_like_is_not_a_filler():
    line = "I would like to open a savings account, please."
    assert _scores(line, line) == (100, 100, 100, 0)


def test_unscripted_fillers_still_count():
    line = "I would like to open a savings account, please."
    _, _, hesitation, fillers = _scores(line, "Um, I would like, like, to open a savings account, you know, please.")
    assert fillers == 3
    assert hesitation < 100


def test_count_fillers_without_alignment_counts_every_filler():
    assert count_fillers(["um", "i", "like", "you", "know", "it"]) == (3, 6)
