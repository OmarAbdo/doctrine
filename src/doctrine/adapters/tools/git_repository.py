"""The git facts doctrine needs: the branch, changed files and files at another commit."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

TIMEOUT_SECONDS = 60


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitRepository:
    root: Path

    def git(self, *arguments: str) -> str:
        finished = subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
        if finished.returncode != 0:
            raise GitError(f"git {' '.join(arguments)}: {finished.stderr.strip()}")
        return finished.stdout

    def current_branch(self) -> str:
        try:
            return self.git("rev-parse", "--abbrev-ref", "HEAD").strip()
        except GitError:
            return ""

    def changed_files(self, base: str) -> list[str]:
        return [
            line for line in self.git("diff", "--name-only", f"{base}...HEAD").splitlines() if line
        ]

    def added_lines(self, base: str) -> int:
        total = 0
        for line in self.git("diff", "--numstat", f"{base}...HEAD").splitlines():
            added, removed, _path = line.split("\t", 2)
            if added.isdigit() and removed.isdigit():
                total += int(added) - int(removed)
        return total

    def file_at(self, revision: str, path: str) -> str | None:
        try:
            return self.git("show", f"{revision}:{path}")
        except GitError:
            return None

    def create_branch(self, name: str) -> None:
        self.git("switch", "-c", name)
