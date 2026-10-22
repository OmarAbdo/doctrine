"""An AI task's eval files in its project: the prompt, the eval set and the recorded runs."""

import json
from pathlib import Path
from typing import Any

from doctrine.domain.evals.cases import EvalCase, parse_cases
from doctrine.domain.evals.results import EvalResult, Version, digest, parse_results, result_line
from doctrine.domain.evals.task import AiTask


def json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class EvalFiles:
    def __init__(self, root: Path, task: AiTask) -> None:
        self.root, self.task = root, task

    def cases(self) -> list[EvalCase]:
        return parse_cases(json_lines(self.root / self.task.cases))

    def version(self) -> Version:
        prompt = (self.root / self.task.prompt).read_text(encoding="utf-8")
        cases = (self.root / self.task.cases).read_text(encoding="utf-8")
        return Version(prompt=digest(prompt), cases=digest(cases))

    def results(self) -> list[EvalResult]:
        return parse_results(json_lines(self.root / self.task.results))

    def record(self, result: EvalResult) -> None:
        append_line(self.root / self.task.results, result_line(result))

    def case_rows(self) -> list[dict[str, Any]]:
        return json_lines(self.root / self.task.cases)

    def add_case(self, row: dict[str, Any]) -> None:
        append_line(self.root / self.task.cases, row)


def append_line(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row) + "\n")
