"""2026-10-22: a project fresh from `doctrine init` failed `doctrine check` (pytest collected no
tests), so its own pre-commit hook refused its first commit."""

from pathlib import Path

from doctrine.adapters.cli.commands.check_commands import check_command


def test_a_fresh_project_passes_the_check(project: Path) -> None:
    assert check_command(project) == 0
