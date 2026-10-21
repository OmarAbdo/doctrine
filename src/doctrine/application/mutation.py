"""Mutation score of a change: the share of mutants on its changed lines that the tests catch."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from doctrine.domain.mutation.operators import mutants

TestsFail = Callable[[str, str], bool]  # (module path, mutated source) -> did the tests fail?


@dataclass(frozen=True)
class ChangedModule:
    path: str
    source: str
    lines: frozenset[int]


@dataclass(frozen=True)
class MutationReport:
    total: int
    survivors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def score(self) -> float:
        """1.0 when nothing changed: there is nothing for the tests to miss."""
        return (self.total - len(self.survivors)) / self.total if self.total else 1.0


def spread[Item](items: list[Item], limit: int) -> list[Item]:
    """At most `limit` items, evenly spread from first to last, the same ones every run."""
    if len(items) <= limit:
        return items
    step = (len(items) - 1) / (limit - 1)
    return [items[round(position * step)] for position in range(limit)]


def run_mutants(
    changed: Sequence[ChangedModule], limit: int, tests_fail: TestsFail
) -> MutationReport:
    candidates = [
        (module.path, mutant)
        for module in changed
        for mutant in mutants(module.source, set(module.lines))
    ]
    chosen = spread(candidates, limit)
    survivors = tuple(
        f"{path}:{mutant.line} {mutant.description}"
        for path, mutant in chosen
        if not tests_fail(path, mutant.source)
    )
    return MutationReport(total=len(chosen), survivors=survivors)
