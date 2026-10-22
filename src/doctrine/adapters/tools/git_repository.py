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

    def changed_lines(self, base: str) -> int:
        """Added plus removed lines: what a reviewer reads, not the net. A line whose only change
        is its ending (CRLF to LF) is not read, so it doesn't count."""
        return sum(line_counts(self, base, "--ignore-cr-at-eol").values())

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


def line_counts(git: GitRepository, base: str, *options: str) -> dict[str, int]:
    """Added plus removed lines per changed file (binary files count none)."""
    counts = {}
    for line in git.git("diff", "--numstat", *options, f"{base}...HEAD").splitlines():
        added, removed, path = line.split("\t", 2)
        counts[path] = int(added) + int(removed) if added.isdigit() else 0
    return counts


def line_ending_only(git: GitRepository, base: str) -> set[str]:
    """Files whose every change is a line ending (with those ignored, git leaves them out)."""
    read = line_counts(git, base, "--ignore-cr-at-eol")
    return {path for path, count in line_counts(git, base).items() if count and path not in read}
