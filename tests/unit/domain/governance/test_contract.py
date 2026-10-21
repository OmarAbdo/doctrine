import pytest

from doctrine.domain.governance.contract import ContractError, parse_contract

VALID = {
    "project": {"name": "jobs", "doctrine_version": "0.1.0", "approver": "OmarAbdo"},
    "outcome": {
        "metric": "applications sent per day",
        "command": ["python", "-m", "jobs.metrics"],
        "baseline": 10,
        "stop_below": 0.8,
    },
    "services": [
        {"name": "core", "path": "src/jobs", "profile": "python", "architecture": "hexagonal"},
    ],
    "limits": {"function_lines": 30},
    "allow": {"suppressions": ["src/jobs/legacy.py:12 vendor quirk"]},
}


def test_a_valid_contract_reads_every_part() -> None:
    contract = parse_contract(VALID)
    assert contract.name == "jobs"
    assert contract.outcome.metric == "applications sent per day"
    assert contract.outcome.command == ("python", "-m", "jobs.metrics")
    assert contract.outcome.stop_value == 8.0
    assert contract.services[0].profile == "python"
    assert contract.limits == {"function_lines": 30}
    assert contract.allowed("suppressions") == ("src/jobs/legacy.py:12 vendor quirk",)


def test_every_problem_is_reported_at_once() -> None:
    broken = {"project": {}, "outcome": {"metric": "x"}, "services": []}
    with pytest.raises(ContractError) as caught:
        parse_contract(broken)
    problems = caught.value.problems
    assert "project.name is missing" in problems
    assert "outcome.command is missing" in problems
    assert "outcome.baseline is missing" in problems
    assert "at least one service is needed" in problems


def test_a_service_needs_a_known_profile_and_architecture() -> None:
    broken = dict(
        VALID,
        services=[{"name": "web", "path": "web", "profile": "cobol", "architecture": "spaghetti"}],
    )
    with pytest.raises(ContractError) as caught:
        parse_contract(broken)
    assert "service web: unknown profile cobol" in caught.value.problems
    assert "service web: unknown architecture spaghetti" in caught.value.problems


def test_stop_below_defaults_to_eighty_percent_of_the_baseline() -> None:
    outcome = dict(VALID["outcome"])
    del outcome["stop_below"]
    contract = parse_contract(dict(VALID, outcome=outcome))
    assert contract.outcome.stop_value == 8.0


def test_the_line_stops_when_the_metric_falls_under_its_stop_value() -> None:
    outcome = parse_contract(VALID).outcome
    assert outcome.line_stopped(7.9) is True
    assert outcome.line_stopped(8.0) is False


def test_ai_tasks_name_their_prompt_command_eval_set_and_minimum() -> None:
    task = {"name": "fit-score", "prompt": "prompts/fit-score.md",
            "command": ["python", "-m", "jobs.adapters.fit_eval"], "minimum": 0.85}
    contract = parse_contract(dict(VALID, ai_tasks=[task]))
    parsed = contract.ai_tasks[0]
    assert parsed.cases == "evals/fit-score/cases.jsonl"
    assert parsed.results == "evals/fit-score/results.jsonl"
    assert parsed.minimum == 0.85


def test_an_ai_task_needs_a_minimum_between_zero_and_one() -> None:
    task = {"name": "fit-score", "prompt": "p.md", "command": ["x"], "minimum": 1.5}
    with pytest.raises(ContractError) as caught:
        parse_contract(dict(VALID, ai_tasks=[task]))
    assert "ai task fit-score: minimum must be between 0 and 1" in caught.value.problems
