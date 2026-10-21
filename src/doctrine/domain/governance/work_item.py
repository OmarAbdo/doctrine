"""A work item: the one change in progress, its kind and the files it may touch."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any

KINDS = frozenset({"feature", "fix", "restore", "refactor", "chore"})
RED_FIRST_KINDS = frozenset({"feature", "fix", "restore"})
ALWAYS_IN_SCOPE = ("tests/**", "work/**")


@dataclass(frozen=True)
class WorkItem:
    id: str
    title: str
    kind: str
    scope: tuple[str, ...]

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")

    @property
    def branch(self) -> str:
        return f"item/{self.id}-{self.slug}"

    @property
    def red_first(self) -> bool:
        """Features, fixes and restores start with a test that fails; refactors keep tests green."""
        return self.kind in RED_FIRST_KINDS

    def covers(self, path: str) -> bool:
        posix = path.replace("\\", "/")
        return any(fnmatch(posix, pattern) for pattern in (*self.scope, *ALWAYS_IN_SCOPE))

    def out_of_scope(self, paths: Iterable[str]) -> list[str]:
        return [path for path in paths if not self.covers(path)]


def scope_problem(scope: tuple[str, ...]) -> str | None:
    if not scope:
        return "an item needs a scope: the folders or files it may change"
    wildcards = [pattern for pattern in scope if pattern.startswith("*")]
    if wildcards:
        return f"a scope names a folder or file, not everything: {wildcards}"
    return None


def parse_work_item(data: Mapping[str, Any]) -> WorkItem:
    if data.get("kind") not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}, not {data.get('kind')!r}")
    scope = tuple(data.get("scope", ()))
    problem = scope_problem(scope)
    if problem:
        raise ValueError(problem)
    return WorkItem(id=str(data["id"]), title=data["title"], kind=data["kind"], scope=scope)
