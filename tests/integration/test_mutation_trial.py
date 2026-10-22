"""Mutation testing against a real project: its changed lines, a copy, its unit tests."""

from pathlib import Path

from support.projects import commit_all, git, write

from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.adapters.tools.mutation_trial import MutantTrial, changed_modules
from doctrine.application.mutation import ChangedModule, run_mutants

ADULT = "def adult(age: int) -> bool:\n    return age >= 18\n"
SHARP_TEST = (
    "from sample_jobs.domain.age import adult\n\n\n"
    "def test_eighteen_is_adult() -> None:\n    assert adult(18) is True\n\n\n"
    "def test_seventeen_is_not() -> None:\n    assert adult(17) is False\n"
)
BLUNT_TEST = (
    "from sample_jobs.domain.age import adult\n\n\ndef test_it_runs() -> None:\n    adult(30)\n"
)


def changed_project(project: Path, test: str) -> list[ChangedModule]:
    git(project, "switch", "-q", "-c", "item/1-age")
    write(project, "src/sample_jobs/domain/age.py", ADULT)
    write(project, "tests/unit/test_age.py", test)
    commit_all(project, "Adults")
    return list(changed_modules(Project.load(project), GitRepository(project), "main"))


def test_only_changed_lines_of_domain_and_application_code_are_mutated(project: Path) -> None:
    changed = changed_project(project, SHARP_TEST)
    assert [(module.path, set(module.lines)) for module in changed] == [
        ("src/sample_jobs/domain/age.py", {1, 2}),
    ]


def test_sharp_tests_kill_the_mutants_and_blunt_ones_let_them_survive(project: Path) -> None:
    changed = changed_project(project, SHARP_TEST)
    with MutantTrial(Project.load(project)) as trial:
        sharp = run_mutants(changed, limit=10, tests_fail=trial.tests_fail)
    assert sharp.score == 1.0
    write(project, "tests/unit/test_age.py", BLUNT_TEST)
    commit_all(project, "Blunter tests")
    with MutantTrial(Project.load(project)) as trial:
        blunt = run_mutants(changed, limit=10, tests_fail=trial.tests_fail)
    assert blunt.score < 0.5
    assert (project / "src/sample_jobs/domain/age.py").read_text(encoding="utf-8") == ADULT
