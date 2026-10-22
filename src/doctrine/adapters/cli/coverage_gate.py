"""`doctrine ci coverage`: the lines a pull request changes must be run by its tests."""

from pathlib import Path

from doctrine.adapters.cli.commands.check_commands import runner_for
from doctrine.adapters.cli.console import complain, load_project, say, shorten

REPORT_FILE = "coverage.xml"


def coverage_command(cwd: Path, base: str) -> int:
    project = load_project(cwd)
    runner = runner_for(project)
    sources = ",".join(service.path for service in project.contract.services)
    tests = sorted({service.tests for service in project.contract.services})
    measured = runner.run("coverage", ["run", f"--source={sources}", "-m", "pytest", "-q", *tests])
    if not measured.passed:
        complain(f"The tests failed under coverage:\n{shorten(measured.output)}")
        return 1
    runner.run("coverage", ["xml", "-o", REPORT_FILE])
    minimum = project.rules.limit("diff_coverage")
    result = runner.run(
        "diff-cover", [REPORT_FILE, f"--compare-branch={base}", f"--fail-under={minimum}"]
    )
    say(shorten(result.output))
    if not result.passed:
        complain(f"Changed lines need at least {minimum}% coverage by tests.")
    return 0 if result.passed else 1
