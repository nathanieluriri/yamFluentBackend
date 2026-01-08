import json
from typing import Dict, List

from schemas.imports import AIGeneratedTurns


def parse_turns(raw_content: str) -> List[Dict[str, str]]:
    parsed = json.loads(raw_content)
    if isinstance(parsed, dict) and "turns" in parsed:
        parsed = parsed["turns"]
    if not isinstance(parsed, list):
        raise ValueError("Model output is not a list")
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError("Model output item is not an object")
        if "role" not in item or "text" not in item:
            raise ValueError("Model output item missing role/text")
        if not str(item.get("text", "")).strip():
            raise ValueError("Model output item has empty text")
    return parsed


def is_strictly_alternating(turns: List[AIGeneratedTurns]) -> bool:
    if not turns or turns[0].role != "ai":
        return False
    expected = "ai"
    for turn in turns:
        if turn.role != expected:
            return False
        expected = "user" if expected == "ai" else "ai"
    return True


def trim_turns(
    turns: List[AIGeneratedTurns],
    target_turns: int,
) -> List[AIGeneratedTurns]:
    if len(turns) <= target_turns:
        return turns
    trimmed = turns[:target_turns]
    if trimmed and trimmed[-1].role != "ai":
        trimmed = trimmed[:-1]
    return trimmed
