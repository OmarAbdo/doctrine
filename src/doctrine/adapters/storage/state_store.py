"""The project's local state (.doctrine/state.json): the active item and unchecked edits."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


STATE_FOLDER = ".doctrine"


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class StateStore:
    root: Path

    @property
    def folder(self) -> Path:
        folder = self.root / STATE_FOLDER
        folder.mkdir(exist_ok=True)
        return folder

    def load(self) -> dict[str, object]:
        path = self.folder / "state.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def update(self, **changes: object) -> None:
        state = {**self.load(), **changes}
        (self.folder / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    def active_item(self) -> str | None:
        item = self.load().get("item")
        return str(item) if item else None

    def unchecked_changes(self) -> bool:
        return bool(self.load().get("unchecked", False))
