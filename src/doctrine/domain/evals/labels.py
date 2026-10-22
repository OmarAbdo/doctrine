"""Omar's labels on real traces (an AI task's input and output): pass or fail with a note. Each
label becomes a case of the task's judge, so the judge is measured against his judgement."""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from doctrine.domain.evals.alignment import VERDICTS
from doctrine.domain.evals.results import digest


@dataclass(frozen=True)
class Trace:
    id: str
    input: Any
    output: Any


def parse_traces(lines: Iterable[Mapping[str, Any]]) -> list[Trace]:
    """A trace without an id is named by its content, so the same trace keeps its name."""
    return [
        Trace(
            id=str(line.get("id") or digest(json.dumps(line, sort_keys=True))),
            input=line.get("input"),
            output=line.get("output"),
        )
        for line in lines
    ]


def label_row(trace: Trace, verdict: str, note: str) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"trace {trace.id}: a label is pass or fail")
    return {
        "id": trace.id,
        "input": {"input": trace.input, "output": trace.output},
        "expected": verdict,
        "note": note.strip(),
    }


def unlabelled(traces: Sequence[Trace], labelled: set[str]) -> list[Trace]:
    return [trace for trace in traces if trace.id not in labelled]
