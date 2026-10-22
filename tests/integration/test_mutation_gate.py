"""`doctrine ci mutation` on a real repository: changed code needs tests that notice it break."""

from pathlib import Path

import pytest
from support.projects import commit_all, git, write

from doctrine.adapters.cli.gates import mutation_gate

ADULT = "def adult(age: int) -> bool:\n    return age >= 18\n"
SHARP_TEST = (
    "from sample_jobs.domain.age import adult\n\n\n"
    "def test_eighteen_is_adult() -> None:\n    assert adult(18) is True\n\n\n"
    "def test_seventeen_is_not() -> None:\n    assert adult(17) is False\n"
)
BLUNT_TEST = (
    "from sample_jobs.domain.age import adult\n\n\ndef test_it_runs() -> None:\n    adult(30)\n"
)


def changed_with(project: Path, test: str) -> None:
    git(project, "switch", "-q", "-c", "item/1-age")
    write(project, "src/sample_jobs/domain/age.py", ADULT)
    write(project, "tests/unit/test_age.py", test)
    commit_all(project, "Adults")


def test_sharp_tests_pass_the_gate(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    changed_with(project, SHARP_TEST)
    assert mutation_gate.mutation_command(project, "main") == 0
    assert "mutants killed" in capsys.readouterr().out


def test_blunt_tests_fail_it_and_the_survivors_are_named(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changed_with(project, BLUNT_TEST)
    assert mutation_gate.mutation_command(project, "main") == 1
    assert "src/sample_jobs/domain/age.py:2" in capsys.readouterr().err


def test_a_change_without_domain_or_application_code_has_nothing_to_mutate(
    project: Path,
) -> None:
    git(project, "switch", "-q", "-c", "item/1-readme")
    write(project, "README.md", "Jobs.\n")
    commit_all(project, "A readme")
    assert mutation_gate.mutation_command(project, "main") == 0
