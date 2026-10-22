"""`doctrine check` and `doctrine test`: the gate every claim of "it works" rests on."""

from pathlib import Path

from doctrine.adapters.cli.console import complain, load_project, say, shorten
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.storage.evidence_log import EvidenceLog
from doctrine.adapters.storage.state_store import StateStore
from doctrine.adapters.tools.subprocess_runner import SubprocessRunner
from doctrine.application.check import CheckReport, check_python_service


def runner_for(project: Project) -> SubprocessRunner:
    roots = [project.root / Path(service.path).parent for service in project.contract.services]
    return SubprocessRunner(project.root, import_roots=[project.root, *roots])


def report_lines(service_name: str, report: CheckReport) -> list[str]:
    lines = [f"{service_name}: {'passed' if report.passed else 'FAILED'}"]
    lines += [f"  {finding}" for finding in report.findings]
    for result in report.failed_tools:
        lines.append(f"  {result.name} failed:\n{shorten(result.output)}")
    return lines


def check_command(cwd: Path) -> int:
    project = load_project(cwd)
    runner, passed = runner_for(project), True
    for service in project.contract.services:
        if service.profile != "python":
            complain(f"{service.name}: the {service.profile} profile isn't built yet; check FAILED")
            passed = False
            continue
        report = check_python_service(service, project.rules, project.sources(service), runner)
        say("\n".join(report_lines(service.name, report)))
        passed = passed and report.passed
    state = StateStore(project.root)
    EvidenceLog(project.root).record("check", "passed" if passed else "failed")
    if passed:
        state.update(unchecked=False, stop_blocks=0)
    return 0 if passed else 1


def test_command(cwd: Path, paths: list[str]) -> int:
    project = load_project(cwd)
    targets = paths or sorted({service.tests for service in project.contract.services})
    result = runner_for(project).run("pytest", ["-q", "-p", "no:cacheprovider", *targets])
    say(shorten(result.output))
    outcome = "green" if result.passed else "red"
    EvidenceLog(project.root).record("test", outcome, detail=" ".join(targets))
    say(f"Recorded a {outcome} test run.")
    return 0 if result.passed else 1
