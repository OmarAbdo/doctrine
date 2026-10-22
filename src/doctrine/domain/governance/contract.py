"""A project's contract (doctrine.toml): outcome metric, services and its own stricter limits."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from doctrine.domain.evals.task import AiTask, ai_task_problems, parse_ai_task

PROFILES = frozenset({"python", "typescript"})
ARCHITECTURES = frozenset({"hexagonal", "layered"})
DEFAULT_STOP_BELOW = 0.8


class ContractError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Outcome:
    metric: str
    command: tuple[str, ...]
    baseline: float
    stop_below: float = DEFAULT_STOP_BELOW

    @property
    def stop_value(self) -> float:
        return self.baseline * self.stop_below

    def line_stopped(self, value: float) -> bool:
        return value < self.stop_value


@dataclass(frozen=True)
class Service:
    name: str
    path: str
    profile: str
    architecture: str
    tests: str = "tests"

    @property
    def package(self) -> str:
        return self.path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Contract:
    name: str
    doctrine_version: str
    approver: str
    outcome: Outcome
    services: tuple[Service, ...]
    limits: Mapping[str, int] = field(default_factory=dict)
    exceptions: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    ai_tasks: tuple[AiTask, ...] = ()

    def allowed(self, kind: str) -> tuple[str, ...]:
        return self.exceptions.get(kind, ())


def missing(section: Mapping[str, Any], prefix: str, keys: tuple[str, ...]) -> list[str]:
    return [f"{prefix}.{key} is missing" for key in keys if key not in section]


def service_problems(services: list[Mapping[str, Any]]) -> list[str]:
    if not services:
        return ["at least one service is needed"]
    problems = []
    for service in services:
        name = service.get("name", "?")
        problems += missing(service, f"service {name}", ("name", "path", "profile", "architecture"))
        if service.get("profile", "python") not in PROFILES:
            problems.append(f"service {name}: unknown profile {service['profile']}")
        if service.get("architecture", "hexagonal") not in ARCHITECTURES:
            problems.append(f"service {name}: unknown architecture {service['architecture']}")
    return problems


def contract_problems(data: Mapping[str, Any]) -> list[str]:
    problems = missing(data.get("project", {}), "project", ("name", "doctrine_version", "approver"))
    problems += missing(data.get("outcome", {}), "outcome", ("metric", "command", "baseline"))
    problems += [problem for task in data.get("ai_tasks", []) for problem in ai_task_problems(task)]
    return problems + service_problems(data.get("services", []))


def parse_outcome(section: Mapping[str, Any]) -> Outcome:
    return Outcome(
        metric=section["metric"],
        command=tuple(section["command"]),
        baseline=float(section["baseline"]),
        stop_below=float(section.get("stop_below", DEFAULT_STOP_BELOW)),
    )


def parse_contract(data: Mapping[str, Any]) -> Contract:
    problems = contract_problems(data)
    if problems:
        raise ContractError(problems)
    return Contract(
        name=data["project"]["name"],
        doctrine_version=data["project"]["doctrine_version"],
        approver=data["project"]["approver"],
        outcome=parse_outcome(data["outcome"]),
        services=tuple(Service(**service) for service in data["services"]),
        limits=dict(data.get("limits", {})),
        exceptions={kind: tuple(entries) for kind, entries in data.get("allow", {}).items()},
        ai_tasks=tuple(parse_ai_task(task) for task in data.get("ai_tasks", [])),
    )
