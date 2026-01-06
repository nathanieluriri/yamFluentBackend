import re
from dataclasses import dataclass
from typing import List, Tuple


_PUNCT_RE = re.compile(r"[^\w\s']")


def tokenize(text: str) -> List[str]:
    cleaned = _PUNCT_RE.sub(" ", text.lower())
    return [token for token in cleaned.split() if token]


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[-1][-1]


def normalized_edit_distance(a: str, b: str) -> float:
    if not a and not b:
        return 0.0
    return edit_distance(a, b) / max(1, len(a), len(b))


@dataclass
class AlignmentResult:
    substitutions: int
    insertions: int
    deletions: int
    aligned_pairs: List[Tuple[str, str]]


def align_words(expected: List[str], actual: List[str]) -> AlignmentResult:
    rows = len(expected) + 1
    cols = len(actual) + 1
    dp = [[0] * cols for _ in range(rows)]
    back = [[None] * cols for _ in range(rows)]

    for i in range(1, rows):
        dp[i][0] = i
        back[i][0] = "del"
    for j in range(1, cols):
        dp[0][j] = j
        back[0][j] = "ins"

    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if expected[i - 1] == actual[j - 1] else 1
            options = [
                (dp[i - 1][j] + 1, "del"),
                (dp[i][j - 1] + 1, "ins"),
                (dp[i - 1][j - 1] + cost, "sub" if cost else "eq"),
            ]
            best_cost, best_op = min(options, key=lambda x: x[0])
            dp[i][j] = best_cost
            back[i][j] = best_op

    i, j = len(expected), len(actual)
    subs = ins = dels = 0
    aligned: List[Tuple[str, str]] = []
    while i > 0 or j > 0:
        op = back[i][j]
        if op == "eq":
            aligned.append((expected[i - 1], actual[j - 1]))
            i -= 1
            j -= 1
        elif op == "sub":
            subs += 1
            aligned.append((expected[i - 1], actual[j - 1]))
            i -= 1
            j -= 1
        elif op == "del":
            dels += 1
            aligned.append((expected[i - 1], ""))
            i -= 1
        elif op == "ins":
            ins += 1
            aligned.append(("", actual[j - 1]))
            j -= 1
        else:
            break

    aligned.reverse()
    return AlignmentResult(subs, ins, dels, aligned)
