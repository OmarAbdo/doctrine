"""Files that belong to doctrine itself and change only through an approved pull request."""

import re

MACHINE_PATHS = ("program files/doctrine", "program files/claudecode", ".claude/settings")
PROJECT_PATHS = (
    ".doctrine/",
    ".git/hooks",
    ".github/workflows/doctrine",
    "codeowners",
    ".github/codeowners",
)
PROTECTED_PATHS = (*MACHINE_PATHS, *PROJECT_PATHS)
# An AI task's recorded runs: the evals gate trusts them, so only `doctrine eval run` writes them.
RECORDED_RUNS = re.compile(r"(?<![\w.-])evals/[^/\s'\"]+/results\.jsonl")
# Work items and the outcome's history: written by `doctrine item` and `doctrine metric record`.
COMMAND_OWNED = re.compile(r"(?<![\w.-])(work/\d+-[^/\s'\"]+\.toml|metrics/outcome\.jsonl)")


def normalise(path: str) -> str:
    return path.replace("\\", "/").lower()


def mentions_protected(text: str) -> bool:
    lowered = normalise(text)
    mentioned = any(fragment in lowered for fragment in PROTECTED_PATHS)
    return mentioned or RECORDED_RUNS.search(lowered) is not None


def mentions_command_owned(text: str) -> bool:
    return COMMAND_OWNED.search(normalise(text)) is not None


def is_protected(path: str, relative: str | None = None) -> bool:
    """Machine files anywhere. A project's own gate files only at its root when the path is
    known relative to the project (`relative`), else wherever they appear."""
    if any(fragment in normalise(path) for fragment in MACHINE_PATHS):
        return True
    if relative is None:
        return mentions_protected(path)
    at_root = normalise(relative)
    return at_root.startswith(PROJECT_PATHS) or RECORDED_RUNS.match(at_root) is not None
