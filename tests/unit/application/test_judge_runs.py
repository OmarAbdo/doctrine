from doctrine.application.evals import record_eval_run
from doctrine.domain.evals.cases import EvalCase
from doctrine.domain.evals.results import EvalResult, Version

LABELS = [
    EvalCase(id=f"{label}-{number}", input="trace", expected=(label,))
    for label, count in (("pass", 9), ("fail", 1))
    for number in range(count)
]


class MemoryStore:
    def __init__(self) -> None:
        self.recorded: list[EvalResult] = []

    def cases(self) -> list[EvalCase]:
        return LABELS

    def version(self) -> Version:
        return Version(prompt="p1", cases="c1")

    def record(self, result: EvalResult) -> None:
        self.recorded.append(result)


class PassEverything:
    def answer(self, case: EvalCase) -> str | None:
        return "pass"


def test_a_judge_run_is_scored_by_its_alignment_with_the_labels() -> None:
    """9 of 10 right, but it catches none of the fails."""
    result = record_eval_run(MemoryStore(), PassEverything(), "2026-10-22T18:00:00Z", judge=True)
    assert result.score == 0.0
    assert result.failures == ("fail-0",)


def test_a_plain_run_is_scored_by_its_share_of_right_answers() -> None:
    result = record_eval_run(MemoryStore(), PassEverything(), "2026-10-22T18:00:00Z")
    assert result.score == 0.9
