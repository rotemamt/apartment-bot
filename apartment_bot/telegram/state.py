import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent.parent / "bot_state.json"


def is_paused() -> bool:
    if not STATE_PATH.exists():
        return False
    return json.loads(STATE_PATH.read_text(encoding="utf-8")).get("paused", False)


def set_paused(value: bool) -> None:
    STATE_PATH.write_text(json.dumps({"paused": value}), encoding="utf-8")
