"""The outcome metric's history (metrics/outcome.jsonl), committed with the project."""

import json
from pathlib import Path

METRIC_FILE = Path("metrics") / "outcome.jsonl"


def latest_metric(root: Path) -> float | None:
    path = root / METRIC_FILE
    if not path.exists():
        return None
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return float(json.loads(lines[-1])["value"]) if lines else None


def append_metric(root: Path, value: float, recorded_at: str) -> None:
    path = root / METRIC_FILE
    path.parent.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"recorded_at": recorded_at, "value": value}) + "\n")
