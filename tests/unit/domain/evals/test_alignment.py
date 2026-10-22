import pytest

from doctrine.domain.evals.alignment import judge_alignment
from doctrine.domain.evals.cases import EvalCase
from doctrine.domain.evals.task import ai_task_problems, parse_ai_task

TASK = {"name": "fit-judge", "prompt": "p.md", "command": ["x"], "minimum": 0.8}


def labelled(passes: int, fails: int) -> list[EvalCase]:
    return [
        EvalCase(id=f"{label}-{number}", input=f"trace {number}", expected=(label,))
        for label, count in (("pass", passes), ("fail", fails))
        for number in range(count)
    ]


def test_a_judge_that_passes_everything_scores_nothing() -> None:
    """Most traces pass, so plain accuracy would rate this judge 0.9."""
    cases = labelled(passes=9, fails=1)
    alignment = judge_alignment(cases, {case.id: "PASS" for case in cases})
    assert (alignment.passes_kept, alignment.fails_caught) == (1.0, 0.0)
    assert alignment.score == 0.0
    assert alignment.failures == ("fail-0",)
    assert alignment.total == 10


def test_the_score_is_the_weaker_of_the_two_rates() -> None:
    cases = labelled(passes=4, fails=2)
    verdicts = {case.id: case.expected[0] for case in cases} | {"pass-0": "fail"}
    del verdicts["fail-1"]
    alignment = judge_alignment(cases, verdicts)
    assert alignment.passes_kept == 0.75
    assert alignment.fails_caught == 0.5
    assert alignment.score == 0.5
    assert alignment.failures == ("pass-0", "fail-1")


def test_without_both_labels_a_judge_cannot_be_measured() -> None:
    assert judge_alignment(labelled(passes=3, fails=0), {}).score == 0.0


def test_an_ai_task_can_be_a_judge() -> None:
    assert parse_ai_task(dict(TASK, judge=True)).judge is True
    assert parse_ai_task(TASK).judge is False
    assert ai_task_problems(dict(TASK, judge="yes")) == [
        "ai task fit-judge: judge must be true or false"
    ]


@pytest.mark.parametrize("label", ["maybe", "ok"])
def test_a_judges_cases_are_labelled_pass_or_fail(label: str) -> None:
    case = EvalCase(id="odd", input="trace", expected=(label,))
    with pytest.raises(ValueError, match="eval case odd: a judge's label is pass or fail"):
        judge_alignment([case], {})
