from doctrine.domain.governance.contract import parse_contract
from doctrine.domain.governance.goalposts import contract_changes
from doctrine.domain.rules.table import parse_rule_table

TABLE = parse_rule_table(
    {"limits": {"function_lines": {"max": 40}, "complexity": {"max": 8}, "name_length": {"min": 3}}}
)

BASE = {
    "project": {"name": "jobs", "doctrine_version": "0.1.0", "approver": "OmarAbdo"},
    "outcome": {"metric": "sent per day", "command": ["python", "-m", "m"], "baseline": 10},
    "services": [{"name": "core", "path": "src", "profile": "python", "architecture": "hexagonal"}],
    "limits": {"function_lines": 30},
}


def changed(**parts: object) -> dict:
    return {**BASE, **parts}


def test_an_unchanged_contract_needs_nothing() -> None:
    assert contract_changes(parse_contract(BASE), parse_contract(BASE), TABLE) == []


def test_tightening_needs_no_approval() -> None:
    after = parse_contract(changed(limits={"function_lines": 25, "complexity": 6}))
    assert contract_changes(parse_contract(BASE), after, TABLE) == []


def test_loosening_a_project_limit_needs_approval() -> None:
    after = parse_contract(changed(limits={"function_lines": 35}))
    assert contract_changes(parse_contract(BASE), after, TABLE) == [
        "limit function_lines: 30 -> 35"
    ]


def test_dropping_a_project_limit_needs_approval() -> None:
    after = parse_contract(changed(limits={}))
    assert contract_changes(parse_contract(BASE), after, TABLE) == [
        "limit function_lines: 30 -> rule table"
    ]


def test_a_new_exception_needs_approval() -> None:
    after = parse_contract(changed(allow={"suppressions": ["src/a.py:3 reason"]}))
    assert contract_changes(parse_contract(BASE), after, TABLE) == [
        "exception added to suppressions: src/a.py:3 reason",
    ]


def test_the_outcome_may_not_move_without_approval() -> None:
    after = parse_contract(
        changed(outcome={"metric": "mails drafted", "command": ["true"], "baseline": 2})
    )
    assert contract_changes(parse_contract(BASE), after, TABLE) == [
        "outcome metric: sent per day -> mails drafted",
        "outcome command changed",
        "outcome baseline: 10 -> 2",
    ]


def test_a_new_doctrine_version_needs_approval() -> None:
    after = parse_contract(
        changed(project={"name": "jobs", "doctrine_version": "0.2.0", "approver": "OmarAbdo"})
    )
    assert contract_changes(parse_contract(BASE), after, TABLE) == [
        "doctrine version: 0.1.0 -> 0.2.0"
    ]


def test_a_service_changing_its_architecture_needs_approval() -> None:
    service = {"name": "core", "path": "src", "profile": "python", "architecture": "layered"}
    after = parse_contract(changed(services=[service]))
    assert contract_changes(parse_contract(BASE), after, TABLE) == [
        "service core: architecture hexagonal -> layered",
    ]




def test_lowering_or_dropping_an_ai_task_needs_approval() -> None:
    task = {"name": "fit", "prompt": "p.md", "command": ["x"], "minimum": 0.9}
    before = parse_contract(changed(ai_tasks=[task]))
    lowered = parse_contract(changed(ai_tasks=[{**task, "minimum": 0.8}]))
    raised = parse_contract(changed(ai_tasks=[{**task, "minimum": 0.95}]))
    assert contract_changes(before, lowered, TABLE) == ["ai task fit: minimum 0.9 -> 0.8"]
    assert contract_changes(before, raised, TABLE) == []
    assert contract_changes(before, parse_contract(BASE), TABLE) == ["ai task fit removed"]
