"""Files that belong to doctrine itself and change only through an approved pull request."""

MACHINE_PATHS = ("program files/doctrine", "program files/claudecode", ".claude/settings")
PROJECT_PATHS = (
    ".doctrine/",
    ".git/hooks",
    ".github/workflows/doctrine",
    "codeowners",
    ".github/codeowners",
)
PROTECTED_PATHS = (*MACHINE_PATHS, *PROJECT_PATHS)


def normalise(path: str) -> str:
    return path.replace("\\", "/").lower()


def mentions_protected(text: str) -> bool:
    lowered = normalise(text)
    return any(fragment in lowered for fragment in PROTECTED_PATHS)


def is_protected(path: str, relative: str | None = None) -> bool:
    """Machine files anywhere. A project's own gate files only at its root when the path is
    known relative to the project (`relative`), else wherever they appear."""
    if any(fragment in normalise(path) for fragment in MACHINE_PATHS):
        return True
    if relative is None:
        return mentions_protected(path)
    return normalise(relative).startswith(PROJECT_PATHS)
