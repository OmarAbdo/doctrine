"""Output for the command line: plain lines on stdout, problems on stderr."""

import sys
from pathlib import Path

from doctrine.adapters.storage.project_files import Project, find_root

OUTPUT_LIMIT = 4000


def say(text: str) -> None:
    sys.stdout.write(text.rstrip() + "\n")


def complain(text: str) -> None:
    sys.stderr.write(text.rstrip() + "\n")


def shorten(text: str) -> str:
    return text if len(text) <= OUTPUT_LIMIT else text[:OUTPUT_LIMIT] + "\n... (cut)"


class NoProjectError(RuntimeError):
    def __init__(self, folder: Path) -> None:
        super().__init__(
            f"{folder} is not inside a doctrine project (no doctrine.toml); "
            "start one with `doctrine init`"
        )


def load_project(cwd: Path) -> Project:
    root = find_root(cwd)
    if root is None:
        raise NoProjectError(cwd)
    return Project.load(root)
