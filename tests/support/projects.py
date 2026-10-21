"""Helpers for tests on a real doctrine project: the template, a git repository, one commit."""

import subprocess
from pathlib import Path

from doctrine.adapters.cli.init_command import init_command

GIT_TIMEOUT_SECONDS = 60


def git(root: Path, *arguments: str) -> str:
    finished = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=True,
    )
    return finished.stdout


def commit_all(root: Path, message: str) -> None:
    git(root, "add", "-A")
    # The project's own pre-commit hook needs an installed doctrine; these tests call it directly.
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message)


def new_project(tmp_path: Path) -> Path:
    root = tmp_path / "jobs"
    root.mkdir()
    assert init_command(root, "Sample Jobs", "OmarAbdo") == 0
    git(root, "config", "user.email", "tests@example.com")
    git(root, "config", "user.name", "Doctrine Tests")
    commit_all(root, "Start from the doctrine template")
    return root


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
