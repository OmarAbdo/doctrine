"""The git facts doctrine needs: the branch, changed files and files at another commit."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

TIMEOUT_SECONDS = 60
# core.fsmonitor starts a background daemon per repository that never exits; doctrine never wants
# one (2026-10-22: 921 of them, from test repositories, ran the PC out of memory).
NO_DAEMON = ("-c", "core.fsmonitor=false")
ITEM_BRANCH = re.compile(r"(?:^|/)item/(\d+)-")


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitRepository:
    root: Path

    def git(self, *arguments: str) -> str:
        finished = subprocess.run(
            ["git", *NO_DAEMON, *arguments],
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

    def highest_item_number(self) -> int:
        """The highest number among item branches, local or remote (item/<n>-<title>)."""
        branches = self.git("branch", "--all", "--format=%(refname:short)").splitlines()
        numbers = [int(match.group(1)) for match in map(ITEM_BRANCH.search, branches) if match]
        return max(numbers, default=0)

    def create_branch(self, name: str) -> None:
        self.git("switch", "-c", name)
