"""Hunter's first pull requests (#62): a new project's gates never started, and once they did, the
coverage gate failed because the project had no tests yet."""

import re
from pathlib import Path

from support.projects import commit_all, git, write

from doctrine.adapters.cli.gates.coverage_gate import coverage_command

GATES = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "project-gates.yml"
PERMISSION = re.compile(r"^\s+([a-z-]+): (read|write)$", re.MULTILINE)


def permissions(block: str) -> set[tuple[str, str]]:
    return set(PERMISSION.findall(block.split("permissions:", 1)[1].split("\n\n", 1)[0]))


def test_the_caller_grants_what_the_shared_gates_request(project: Path) -> None:
    """A called workflow gets no more than its caller grants; new repositories grant almost none."""
    caller = (project / ".github" / "workflows" / "doctrine.yml").read_text(encoding="utf-8")
    requested = permissions(GATES.read_text(encoding="utf-8"))
    assert requested
    assert requested <= permissions(caller.split("gates:", 1)[1])


def test_a_project_without_tests_yet_passes_the_coverage_gate(project: Path) -> None:
    git(project, "switch", "-q", "-c", "item/1-readme")
    write(project, "README.md", "Hunter.\n")
    commit_all(project, "A readme")
    assert coverage_command(project, "main") == 0
