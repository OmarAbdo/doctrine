"""A judge: an AI task that says pass or fail on another task's output, measured against Omar's
pass and fail labels. Plain accuracy flatters a judge that passes everything when most outputs pass,
so its score is the lower of two rates: the share of his passes it passes and the share of his fails
it fails. Without both kinds of label it cannot be measured and scores nothing."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from doctrine.domain.evals.cases import EvalCase
from doctrine.domain.evals.scoring import normalise

VERDICTS = ("pass", "fail")


@dataclass(frozen=True)
class Alignment:
    passes_kept: float
    fails_caught: float
    total: int
    failures: tuple[str, ...]

    @property
    def score(self) -> float:
        return min(self.passes_kept, self.fails_caught)


def label_of(case: EvalCase) -> str:
    label = normalise(case.expected[0]) if len(case.expected) == 1 else ""
    if label not in VERDICTS:
        raise ValueError(f"eval case {case.id}: a judge's label is pass or fail")
    return label


def share_right(labels: Mapping[str, str], wrong: Sequence[str], verdict: str) -> float:
    labelled = [case_id for case_id, label in labels.items() if label == verdict]
    right = [case_id for case_id in labelled if case_id not in wrong]
    return len(right) / len(labelled) if labelled else 0.0


def judge_alignment(cases: Sequence[EvalCase], verdicts: Mapping[str, str]) -> Alignment:
    labels = {case.id: label_of(case) for case in cases}
    wrong = tuple(
        case_id
        for case_id, label in labels.items()
        if normalise(verdicts.get(case_id, "")) != label
    )
    return Alignment(
        passes_kept=share_right(labels, wrong, "pass"),
        fails_caught=share_right(labels, wrong, "fail"),
        total=len(cases),
        failures=wrong,
    )
