import pytest

from doctrine.domain.evals.results import EvalResult, Version, eval_problems, parse_results
from doctrine.domain.evals.task import AiTask

TASK = AiTask(name="fit", prompt="prompts/fit.md", command=("run",), minimum=0.8)


def result(prompt: str, cases: str, score: float) -> EvalResult:
    return EvalResult(
        prompt=prompt,
        cases=cases,
        score=score,
        total=20,
        failures=(),
        recorded_at="2026-10-22T15:00:00Z",
    )


def test_results_are_read_from_their_json_lines() -> None:
    lines = [
        {
            "prompt": "p1",
            "cases": "c1",
            "score": 0.9,
            "total": 20,
            "failures": ["a", "b"],
            "recorded_at": "2026-10-22T15:00:00Z",
        }
    ]
    assert parse_results(lines) == [
        EvalResult(
            prompt="p1",
            cases="c1",
            score=0.9,
            total=20,
            failures=("a", "b"),
            recorded_at="2026-10-22T15:00:00Z",
        ),
    ]


def test_a_changed_prompt_needs_a_recorded_run_on_its_own_version() -> None:
    verdict = eval_problems(TASK, Version("p2", "c1"), head=[result("p1", "c1", 0.9)], base=[])
    assert verdict.refusals == [
        "fit: no eval run for this prompt and eval set: run `doctrine eval run fit`"
    ]


def test_a_score_under_the_minimum_is_refused() -> None:
    verdict = eval_problems(TASK, Version("p2", "c1"), head=[result("p2", "c1", 0.7)], base=[])
    assert verdict.refusals == ["fit: scores 0.7 on its eval set; the minimum is 0.8"]


def test_a_lower_score_on_the_same_eval_set_needs_the_approver() -> None:
    base = [result("p1", "c1", 0.95)]
    verdict = eval_problems(
        TASK, Version("p2", "c1"), head=[*base, result("p2", "c1", 0.85)], base=base
    )
    assert verdict.refusals == []
    assert verdict.approvals == ["fit: scores 0.85, down from 0.95 on the same eval set"]


def test_a_grown_eval_set_is_judged_by_the_minimum_only() -> None:
    base = [result("p1", "c1", 0.95)]
    verdict = eval_problems(
        TASK, Version("p1", "c2"), head=[*base, result("p1", "c2", 0.85)], base=base
    )
    assert (verdict.refusals, verdict.approvals) == ([], [])


@pytest.mark.parametrize("score", [0.95, 1.0])
def test_an_equal_or_better_score_passes(score: float) -> None:
    base = [result("p1", "c1", 0.95)]
    verdict = eval_problems(
        TASK, Version("p2", "c1"), head=[*base, result("p2", "c1", score)], base=base
    )
    assert (verdict.refusals, verdict.approvals) == ([], [])
