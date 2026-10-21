from pathlib import Path

from support.projects import commit_all, write

from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.adapters.tools.subprocess_runner import SubprocessRunner


def test_git_reports_the_branch_the_changes_and_old_versions(project: Path) -> None:
    repository = GitRepository(project)
    assert repository.current_branch() == "main"
    repository.create_branch("item/1-search")
    write(project, "src/sample_jobs/domain/search.py", "LIMIT = 10\nOFFSET = 0\n")
    commit_all(project, "Add search")
    assert repository.current_branch() == "item/1-search"
    assert repository.changed_files("main") == ["src/sample_jobs/domain/search.py"]
    assert repository.added_lines("main") == 2
    assert repository.file_at("main", "src/sample_jobs/domain/search.py") is None
    assert "LIMIT" in (repository.file_at("HEAD", "src/sample_jobs/domain/search.py") or "")


def test_the_runner_reports_a_passing_and_a_failing_tool(project: Path) -> None:
    write(project, "tests/unit/test_truth.py", "def test_truth() -> None:\n    assert 1 + 1 == 2\n")
    write(project, "tests/unit/test_lie.py", "def test_lie() -> None:\n    assert 1 + 1 == 3\n")
    runner = SubprocessRunner(project, import_roots=[project / "src"])
    assert runner.run("pytest", ["-q", "tests/unit/test_truth.py"]).passed
    failing = runner.run("pytest", ["-q", "tests/unit/test_lie.py"])
    assert not failing.passed
    assert "test_lie" in failing.output
