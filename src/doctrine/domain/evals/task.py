"""An AI task of a project: its prompt, the command that runs it on an eval set, and the minimum
share of cases it must get right."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AiTask:
    name: str
    prompt: str
    command: tuple[str, ...]
    minimum: float
    judge: bool = False

    @property
    def cases(self) -> str:
        return f"evals/{self.name}/cases.jsonl"

    @property
    def results(self) -> str:
        return f"evals/{self.name}/results.jsonl"


def ai_task_problems(task: Mapping[str, Any]) -> list[str]:
    name = task.get("name", "?")
    problems = [
        f"ai task {name}: {key} is missing"
        for key in ("name", "prompt", "command", "minimum")
        if key not in task
    ]
    minimum = task.get("minimum", 0)
    if not isinstance(minimum, (int, float)) or not 0 <= minimum <= 1:
        problems.append(f"ai task {name}: minimum must be between 0 and 1")
    if not isinstance(task.get("judge", False), bool):
        problems.append(f"ai task {name}: judge must be true or false")
    return problems


def parse_ai_task(task: Mapping[str, Any]) -> AiTask:
    return AiTask(
        name=task["name"],
        prompt=task["prompt"],
        command=tuple(task["command"]),
        minimum=float(task["minimum"]),
        judge=task.get("judge", False),
    )
