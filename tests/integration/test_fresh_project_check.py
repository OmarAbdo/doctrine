"""2026-10-22: a project fresh from `doctrine init` failed `doctrine check` (pytest collected no
tests), so its own pre-commit hook refused its first commit."""

from pathlib import Path

from support.projects import commit_all, git, write

from doctrine.adapters.cli.commands.check_commands import check_command
from doctrine.adapters.cli.gates import red_first
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.git_repository import GitRepository

WORDS = "def test_words() -> None:\n    print('no tests ran')\n    assert False\n"


def test_a_fresh_project_passes_the_check(project: Path) -> None:
    assert check_command(project) == 0


def test_red_first_reads_pytests_exit_code_not_its_output(project: Path) -> None:
    """#54's own CI: a failing test that printed "no tests ran" was taken for an empty file."""
    git(project, "switch", "-q", "-c", "item/1-words")
    write(project, "tests/unit/test_words.py", WORDS)
    commit_all(project, "A failing test that talks")
    verdict = red_first.tests_fail_on_base(Project.load(project), GitRepository(project), "main")
    assert verdict.ok, verdict.message
