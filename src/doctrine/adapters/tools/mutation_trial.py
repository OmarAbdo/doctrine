"""Mutation testing on a real project: the lines a change touched in its domain and application
code, and its unit tests run against one mutant at a time in a copy of the project (the project
itself is never modified)."""

import re
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.adapters.tools.subprocess_runner import SubprocessRunner
from doctrine.application.mutation import ChangedModule

HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", re.MULTILINE)
# Adapters are covered by integration tests, which are too slow to run once per mutant.
MUTATED_LAYERS = frozenset({"domain", "application"})
NOT_COPIED = shutil.ignore_patterns(".git", ".venv*", "__pycache__", ".doctrine", "*_cache")


def mutable(project: Project, path: str) -> bool:
    for service in project.contract.services:
        prefix = service.path.rstrip("/") + "/"
        if path.startswith(prefix) and path.endswith(".py"):
            layer = path.removeprefix(prefix).split("/")[0]
            return service.architecture != "hexagonal" or layer in MUTATED_LAYERS
    return False


def changed_lines(diff: str) -> frozenset[int]:
    """The new side's line numbers of every hunk in a `git diff -U0`."""
    lines: set[int] = set()
    for hunk in HUNK.finditer(diff):
        start, count = int(hunk.group(1)), int(hunk.group(2) or 1)
        lines.update(range(start, start + count))
    return frozenset(lines)


def changed_modules(project: Project, git: GitRepository, base: str) -> Iterator[ChangedModule]:
    for path in git.changed_files(base):
        if not mutable(project, path) or not (project.root / path).exists():
            continue
        lines = changed_lines(git.git("diff", "-U0", f"{base}...HEAD", "--", path))
        source = (project.root / path).read_text(encoding="utf-8")
        if lines:
            yield ChangedModule(path=path, source=source, lines=lines)


class MutantTrial:
    """A copy of the project in which one mutant at a time replaces its module."""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.folder = Path(tempfile.mkdtemp(prefix="doctrine-mutants-"))
        self.copy = self.folder / "project"

    def __enter__(self) -> "MutantTrial":
        shutil.copytree(self.project.root, self.copy, ignore=NOT_COPIED)
        return self

    def __exit__(self, *details: object) -> None:
        shutil.rmtree(self.folder, ignore_errors=True)

    def runner(self) -> SubprocessRunner:
        services = self.project.contract.services
        roots = [self.copy, *(self.copy / Path(service.path).parent for service in services)]
        return SubprocessRunner(self.copy, import_roots=roots)

    def tests_fail(self, path: str, mutated: str) -> bool:
        """Whether the unit tests catch this mutant of `path`."""
        target = self.copy / path
        original = target.read_text(encoding="utf-8")
        target.write_text(mutated, encoding="utf-8")
        unit = sorted(
            {f"{service.tests.rstrip('/')}/unit" for service in self.project.contract.services}
        )
        try:
            result = self.runner().run("pytest", ["-x", "-q", "-p", "no:cacheprovider", *unit])
            return not result.passed
        finally:
            target.write_text(original, encoding="utf-8")
