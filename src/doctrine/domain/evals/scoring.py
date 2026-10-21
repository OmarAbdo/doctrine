"""Scoring an AI task's outputs against its eval set: the share of cases it got right."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from doctrine.domain.evals.cases import EvalCase


@dataclass(frozen=True)
class EvalRun:
    total: int
    failures: tuple[str, ...] = field(default_factory=tuple)

    @property
    def score(self) -> float:
        return (self.total - len(self.failures)) / self.total if self.total else 0.0


def normalise(answer: str) -> str:
    return " ".join(answer.split()).casefold()


def answered_right(case: EvalCase, output: str | None) -> bool:
    return output is not None and normalise(output) in {
        normalise(answer) for answer in case.expected
    }


def score_outputs(cases: Sequence[EvalCase], outputs: Mapping[str, str]) -> EvalRun:
    failures = tuple(case.id for case in cases if not answered_right(case, outputs.get(case.id)))
    return EvalRun(total=len(cases), failures=failures)
