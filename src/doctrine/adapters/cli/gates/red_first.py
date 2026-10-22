"""The proof that a test was written first: the item's new tests must fail on the code before it."""

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.adapters.tools.subprocess_runner import SubprocessRunner

NO_TESTS_COLLECTED = 5


@dataclass(frozen=True)
class RedFirstVerdict:
    ok: bool
    message: str


def changed_tests(project: Project, git: GitRepository, base: str) -> list[str]:
    roots = tuple(service.tests.rstrip("/") + "/" for service in project.contract.services)
    added_or_modified = git.git(
        "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD"
    ).splitlines()
    return [
        path
        for path in added_or_modified
        if path.startswith(roots) and PurePosixPath(path).name.startswith("test_")
    ]


def run_on_base(project: Project, git: GitRepository, base: str, tests: list[str]) -> int:
    folder = Path(tempfile.mkdtemp(prefix="doctrine-base-"))
    try:
        git.git("worktree", "add", "--detach", str(folder / "tree"), base)
        tree = folder / "tree"
        for path in tests:
            (tree / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(project.root / path, tree / path)
        roots = [tree, *(tree / Path(service.path).parent for service in project.contract.services)]
        result = SubprocessRunner(tree, import_roots=roots).run(
            "pytest", ["-q", "-p", "no:cacheprovider", *tests]
        )
        return (
            0 if result.passed else (NO_TESTS_COLLECTED if "no tests ran" in result.output else 1)
        )
    finally:
        git.git("worktree", "remove", "--force", str(folder / "tree"))
        shutil.rmtree(folder, ignore_errors=True)


def tests_fail_on_base(project: Project, git: GitRepository, base: str) -> RedFirstVerdict:
    tests = changed_tests(project, git, base)
    if not tests:
        return RedFirstVerdict(
            ok=False, message="This item needs a new or changed test; there is none."
        )
    outcome = run_on_base(project, git, base, tests)
    if outcome == 0:
        return RedFirstVerdict(
            ok=False,
            message=f"{', '.join(tests)} pass on the code before this item: "
            "they prove nothing about it.",
        )
    if outcome == NO_TESTS_COLLECTED:
        return RedFirstVerdict(ok=False, message="The changed test files hold no tests.")
    return RedFirstVerdict(
        ok=True, message=f"{', '.join(tests)} fail on the code before this item: written first."
    )
