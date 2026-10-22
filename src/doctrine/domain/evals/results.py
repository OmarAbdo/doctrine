"""Recorded eval runs (evals/<task>/results.jsonl) and the rule a changed prompt must pass.

A run is recorded per prompt version and eval set version (their content digests). A pull request
that changes either needs a recorded run on the new versions: under the task's minimum it is
refused; lower than before on the same eval set it needs the approver; a grown eval set is judged
by the minimum only, since new cases are meant to be hard.
"""

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from doctrine.domain.evals.task import AiTask


@dataclass(frozen=True)
class EvalResult:
    prompt: str
    cases: str
    score: float
    total: int
    failures: tuple[str, ...]
    recorded_at: str


@dataclass(frozen=True)
class Version:
    """Content digests of the prompt and of the eval set a run was made with."""

    prompt: str
    cases: str


def digest(text: str) -> str:
    """A content digest that a Windows checkout (CRLF) and a Linux one (LF) agree on."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()[:16]


def result_line(result: EvalResult) -> dict[str, Any]:
    return {**asdict(result), "failures": list(result.failures)}


@dataclass(frozen=True)
class EvalVerdict:
    refusals: list[str] = field(default_factory=list)
    approvals: list[str] = field(default_factory=list)


def parse_results(lines: Iterable[Mapping[str, Any]]) -> list[EvalResult]:
    return [
        EvalResult(
            prompt=str(line["prompt"]),
            cases=str(line["cases"]),
            score=float(line["score"]),
            total=int(line["total"]),
            failures=tuple(line.get("failures", ())),
            recorded_at=str(line["recorded_at"]),
        )
        for line in lines
    ]


def latest(results: Sequence[EvalResult], version: Version) -> EvalResult | None:
    matching = [
        run for run in results if (run.prompt, run.cases) == (version.prompt, version.cases)
    ]
    return matching[-1] if matching else None


def best_on(results: Sequence[EvalResult], cases: str) -> float | None:
    scores = [run.score for run in results if run.cases == cases]
    return max(scores) if scores else None


def eval_problems(
    task: AiTask, version: Version, head: Sequence[EvalResult], base: Sequence[EvalResult]
) -> EvalVerdict:
    name, run = task.name, latest(head, version)
    if run is None:
        missing = "no eval run for this prompt and eval set"
        return EvalVerdict(refusals=[f"{name}: {missing}: run `doctrine eval run {name}`"])
    if run.score < task.minimum:
        low = f"scores {run.score:g} on its eval set; the minimum is {task.minimum:g}"
        return EvalVerdict(refusals=[f"{name}: {low}"])
    before = best_on(base, version.cases)
    if before is not None and run.score < before:
        down = f"scores {run.score:g}, down from {before:g} on the same eval set"
        return EvalVerdict(approvals=[f"{name}: {down}"])
    return EvalVerdict()
