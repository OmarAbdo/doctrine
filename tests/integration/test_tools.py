import subprocess
import sys
import time
from pathlib import Path

import pytest
from support.projects import commit_all, git, write

from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.adapters.tools.subprocess_runner import SubprocessRunner

DAEMON_COUNT = (
    "@(Get-CimInstance Win32_Process -Filter \"name='git.exe'\" | "
    "Where-Object { $_.CommandLine -match 'fsmonitor--daemon' }).Count"
)


def fsmonitor_daemons() -> int:
    finished = subprocess.run(
        ["powershell", "-NoProfile", "-Command", DAEMON_COUNT],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return int(finished.stdout.strip())


def test_every_git_call_doctrine_makes_has_fsmonitor_off(project: Path) -> None:
    """The proof on every platform: whatever a repository's config says, doctrine's git calls
    run with core.fsmonitor=false."""
    git(project, "config", "core.fsmonitor", "true")
    assert GitRepository(project).git("config", "--get", "core.fsmonitor").strip() == "false"


@pytest.mark.skipif(
    sys.platform != "win32", reason="the fsmonitor daemon is a Windows/macOS feature"
)
def test_doctrine_starts_no_fsmonitor_daemon_even_where_git_is_told_to(project: Path) -> None:
    """2026-10-22: with core.fsmonitor on, every throwaway test repository left a daemon behind;
    921 of them ran the PC out of memory."""
    git(project, "config", "core.fsmonitor", "true")
    before = fsmonitor_daemons()
    try:
        write(project, "notes.md", "changed\n")
        GitRepository(project).git("status")
        GitRepository(project).git("add", "-A")
        commit_all(project, "A change")
        time.sleep(2)
        assert fsmonitor_daemons() == before
    finally:
        subprocess.run(
            ["git", "fsmonitor--daemon", "stop"],
            cwd=project,
            capture_output=True,
            timeout=60,
            check=False,
        )


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
