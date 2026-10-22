from doctrine.application.evals import record_eval_run
from doctrine.domain.evals.cases import EvalCase
from doctrine.domain.evals.results import EvalResult, Version

CASES = [
    EvalCase(id="yes", input="2+2", expected=("4", "four")),
    EvalCase(id="no", input="3+3", expected=("6",)),
    EvalCase(id="silent", input="?", expected=("anything",)),
]


class MemoryStore:
    def __init__(self) -> None:
        self.recorded: list[EvalResult] = []

    def cases(self) -> list[EvalCase]:
        return CASES

    def version(self) -> Version:
        return Version(prompt="p1", cases="c1")

    def record(self, result: EvalResult) -> None:
        self.recorded.append(result)


class Guesser:
    """Right on the first case, wrong on the second and silent on the third."""

    def answer(self, case: EvalCase) -> str | None:
        return {"yes": " Four ", "no": "7"}.get(case.id)


def test_a_run_is_scored_and_recorded_for_its_version() -> None:
    store = MemoryStore()
    result = record_eval_run(store, Guesser(), "2026-10-22T16:00:00Z")
    assert result == EvalResult(
        prompt="p1",
        cases="c1",
        score=1 / 3,
        total=3,
        failures=("no", "silent"),
        recorded_at="2026-10-22T16:00:00Z",
    )
    assert store.recorded == [result]
