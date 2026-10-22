from pathlib import Path

import pytest
from support.projects import commit_all, git, write

from doctrine.adapters.cli.gates.coverage_gate import coverage_command
from doctrine.adapters.cli.commands.selftest_command import selftest_command

COVERED = "def double(number: int) -> int:\n    return number * 2\n"
TEST = (
    "from sample_jobs.domain.doubling import double\n\n\n"
    "def test_double() -> None:\n    assert double(2) == 4\n"
)
UNCOVERED = "def triple(number: int) -> int:\n    return number * 3\n"


def test_changed_lines_without_a_test_fail_the_coverage_gate(project: Path) -> None:
    git(project, "switch", "-q", "-c", "item/1-doubling")
    write(project, "src/sample_jobs/domain/doubling.py", COVERED)
    write(project, "tests/unit/test_doubling.py", TEST)
    commit_all(project, "Doubling with its test")
    assert coverage_command(project, "main") == 0
    write(project, "src/sample_jobs/domain/tripling.py", UNCOVERED)
    commit_all(project, "Tripling without a test")
    assert coverage_command(project, "main") == 1


def test_the_selftest_catches_every_sample_and_attack(capsys: pytest.CaptureFixture[str]) -> None:
    assert selftest_command() == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[-1] == "1", lines
