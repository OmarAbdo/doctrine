"""The evidence log: an append-only chain of test runs, checks and proofs, each linked by digest."""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Evidence:
    kind: str  # test, check, proof, metric
    outcome: str  # red, green, passed, failed, or the metric's value
    item: str
    recorded_at: str
    detail: str = ""
    previous: str = ""
    digest: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def expected_digest(self) -> str:
        payload = {key: value for key, value in self.as_dict().items() if key != "digest"}
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def link(previous: Evidence | None, **fields: str) -> Evidence:
    unsealed = Evidence(**fields, previous=previous.digest if previous else "")
    return Evidence(**{**unsealed.as_dict(), "digest": unsealed.expected_digest()})


def first_broken_link(chain: list[Evidence]) -> int | None:
    expected_previous = ""
    for position, entry in enumerate(chain):
        if entry.previous != expected_previous or entry.digest != entry.expected_digest():
            return position
        expected_previous = entry.digest
    return None


def item_not_ready(chain: list[Evidence], item_id: str, *, red_first: bool) -> str | None:
    """Why an item can't be called done yet, or None when the evidence supports it."""
    own = [entry for entry in chain if entry.item == item_id]
    if red_first and not any(entry.kind == "test" and entry.outcome == "red" for entry in own):
        return "it is a feature or fix with no recorded failing test (`doctrine test` while red)"
    checks = [position for position, entry in enumerate(own) if entry.kind == "check"]
    if not checks or own[checks[-1]].outcome != "passed":
        return "its last `doctrine check` didn't pass, or there is none"
    if any(entry.kind == "test" and entry.outcome == "red" for entry in own[checks[-1] :]):
        return "a test went red after the last passing `doctrine check`; run it again"
    return None
