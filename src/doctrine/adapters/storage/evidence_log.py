"""The evidence log (.doctrine/evidence.jsonl): test runs, checks and proofs, chained by digest."""

import json
from dataclasses import dataclass
from pathlib import Path

from doctrine.adapters.storage.state_store import StateStore, now
from doctrine.domain.governance.evidence import Evidence, first_broken_link, link


class TamperedLogError(RuntimeError):
    def __init__(self, position: int) -> None:
        super().__init__(
            f"the evidence log was edited by hand at entry {position}; "
            "doctrine trusts nothing in it until Omar resets it"
        )


@dataclass
class EvidenceLog:
    root: Path

    @property
    def path(self) -> Path:
        return StateStore(self.root).folder / "evidence.jsonl"

    def entries(self) -> list[Evidence]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [Evidence(**json.loads(line)) for line in lines if line.strip()]

    def record(self, kind: str, outcome: str, detail: str = "") -> Evidence:
        chain = self.entries()
        broken = first_broken_link(chain)
        if broken is not None:
            raise TamperedLogError(broken)
        item = StateStore(self.root).active_item() or ""
        entry = link(
            chain[-1] if chain else None,
            kind=kind,
            outcome=outcome,
            item=item,
            recorded_at=now(),
            detail=detail,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.as_dict(), ensure_ascii=False) + "\n")
        return entry

    def red_seen(self, item_id: str) -> bool:
        return any(
            entry.kind == "test" and entry.outcome == "red" and entry.item == item_id
            for entry in self.entries()
        )
