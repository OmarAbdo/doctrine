"""`doctrine ci mutation`: the tests must notice when the domain and application code a pull
request changed is broken on purpose (mutants); the share they catch must reach the rule table's
mutation_score."""

from pathlib import Path

from doctrine.adapters.cli.console import complain, load_project, say
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.adapters.tools.mutation_trial import MutantTrial, changed_modules
from doctrine.application.mutation import run_mutants

# Each mutant runs the unit tests once; a sample spread over the change keeps CI to minutes.
MUTANTS_PER_PULL_REQUEST = 30


def mutation_command(cwd: Path, base: str) -> int:
    project = load_project(cwd)
    changed = list(changed_modules(project, GitRepository(project.root), base))
    if not changed:
        say("No domain or application code changed: nothing to mutate.")
        return 0
    with MutantTrial(project) as trial:
        report = run_mutants(changed, MUTANTS_PER_PULL_REQUEST, trial.tests_fail)
    minimum = project.rules.limit("mutation_score")
    killed = report.total - len(report.survivors)
    say(f"{killed} of {report.total} mutants killed ({report.score:.0%}; minimum {minimum}%).")
    if report.score * 100 >= minimum:
        return 0
    for survivor in report.survivors:
        complain(f"  survived: {survivor}")
    complain("The tests don't notice these changes: assert what the changed code does.")
    return 1
