"""Running an AI task on its eval set and recording the result for the prompt and eval set used."""

from typing import Protocol

from doctrine.domain.evals.cases import EvalCase
from doctrine.domain.evals.results import EvalResult, Version
from doctrine.domain.evals.scoring import score_outputs


class EvalStore(Protocol):
    def cases(self) -> list[EvalCase]: ...

    def version(self) -> Version: ...

    def record(self, result: EvalResult) -> None: ...


class Answerer(Protocol):
    def answer(self, case: EvalCase) -> str | None: ...


def record_eval_run(store: EvalStore, task: Answerer, recorded_at: str) -> EvalResult:
    cases, version = store.cases(), store.version()
    answers = {case.id: task.answer(case) for case in cases}
    run = score_outputs(cases, {key: value for key, value in answers.items() if value is not None})
    result = EvalResult(
        prompt=version.prompt,
        cases=version.cases,
        score=run.score,
        total=run.total,
        failures=run.failures,
        recorded_at=recorded_at,
    )
    store.record(result)
    return result
