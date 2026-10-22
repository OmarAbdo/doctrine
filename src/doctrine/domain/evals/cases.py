"""An eval set: cases with an input and every answer that counts as right, labelled by Omar."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    id: str
    input: Any
    expected: tuple[str, ...]


def expected_answers(raw: Any) -> tuple[str, ...]:
    answers = raw if isinstance(raw, list) else [raw]
    return tuple(str(answer) for answer in answers if answer is not None)


def parse_case(number: int, line: Mapping[str, Any]) -> EvalCase:
    case_id = str(line.get("id") or "")
    if not case_id:
        raise ValueError(f"eval case on line {number} has no id")
    expected = expected_answers(line.get("expected"))
    if not expected:
        raise ValueError(f"eval case {case_id} has no expected answer")
    return EvalCase(id=case_id, input=line.get("input"), expected=expected)


def parse_cases(lines: Iterable[Mapping[str, Any]]) -> list[EvalCase]:
    cases = [parse_case(number, line) for number, line in enumerate(lines, start=1)]
    seen: set[str] = set()
    for case in cases:
        if case.id in seen:
            raise ValueError(f"eval case {case.id} appears twice")
        seen.add(case.id)
    return cases
