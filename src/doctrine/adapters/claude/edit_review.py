"""A quick review of the one file Claude just changed: formatted, then linted."""

from pathlib import Path

from doctrine.adapters.storage.project_files import Project, find_root
from doctrine.adapters.storage.state_store import StateStore
from doctrine.adapters.tools.subprocess_runner import SubprocessRunner
from doctrine.application.check import source_limits
from doctrine.application.python_tools import ruff_check
from doctrine.domain.python.source import module_findings


def file_problems(project: Project, path: Path) -> list[str]:
    runner = SubprocessRunner(project.root, import_roots=[project.root])
    line_length = f"--line-length={project.rules.limit('line_length')}"
    runner.run("ruff-format", ["format", "--no-cache", line_length, str(path)])
    result = runner.run("ruff", ruff_check(project.rules, [str(path)]).arguments)
    problems = [] if result.passed else [result.output]
    if not is_service_source(project, path):
        return problems
    source = path.read_text(encoding="utf-8")
    findings = module_findings(path.name, source, source_limits(project.rules))
    return problems + [str(finding) for finding in findings]


def is_service_source(project: Project, path: Path) -> bool:
    """Doctrine's own source rules apply where `doctrine check` applies them: service code."""
    relative = path.resolve().relative_to(project.root.resolve()).as_posix()
    return any(
        relative.startswith(service.path.rstrip("/") + "/") for service in project.contract.services
    )


def review_edit(path: Path) -> list[str]:
    """Marks the project's changes unchecked and returns the problems in the changed file."""
    root = find_root(path.parent)
    if root is None:
        return []
    StateStore(root).update(unchecked=True)
    if path.suffix != ".py" or not path.exists():
        return []
    return file_problems(Project.load(root), path)
