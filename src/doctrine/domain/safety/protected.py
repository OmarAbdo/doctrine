"""Files that belong to doctrine itself and change only through an approved pull request."""

PROTECTED_PATHS = (
    ".doctrine/",
    "program files/doctrine",
    "program files/claudecode",
    ".git/hooks",
    ".github/workflows/doctrine",
    "codeowners",
    ".claude/settings",
)


def normalise(path: str) -> str:
    return path.replace("\\", "/").lower()


def mentions_protected(text: str) -> bool:
    lowered = normalise(text)
    return any(fragment in lowered for fragment in PROTECTED_PATHS)


def is_protected(path: str) -> bool:
    return mentions_protected(path)
