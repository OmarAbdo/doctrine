from doctrine.domain.governance.contract import parse_contract
from doctrine.domain.governance.goalposts import ai_task_changes

BASE = {
    "project": {"name": "jobs", "doctrine_version": "0.1.0", "approver": "OmarAbdo"},
    "outcome": {"metric": "m", "command": ["x"], "baseline": 1, "stop_below": 0.5},
    "services": [
        {"name": "core", "path": "src/jobs", "profile": "python", "architecture": "hexagonal"},
    ],
}
JUDGE = {"name": "fit-judge", "prompt": "p.md", "command": ["x"], "minimum": 0.8, "judge": True}


def test_a_judge_scored_as_a_plain_task_needs_approval() -> None:
    """Plain accuracy rates a judge that passes everything highly when most traces pass."""
    before = parse_contract(dict(BASE, ai_tasks=[JUDGE]))
    plain = parse_contract(dict(BASE, ai_tasks=[dict(JUDGE, judge=False)]))
    assert ai_task_changes(before, plain) == ["ai task fit-judge: no longer a judge"]
    assert ai_task_changes(plain, before) == []
