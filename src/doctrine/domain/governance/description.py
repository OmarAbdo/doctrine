"""A pull request's description: what changed, why, the proof, and what is not verified."""

import re

REQUIRED = ("What changed", "Why", "Proof", "Not verified")
PLACEHOLDERS = frozenset({"", "-", "todo", "tbd", "n/a", "..."})
HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)  # the template's hints are no answer


def sections(body: str) -> dict[str, str]:
    """Each '## Heading' (lower case) with the text under it."""
    found: dict[str, str] = {}
    matches = list(HEADING.finditer(body))
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(body)
        found[match.group(1).casefold()] = COMMENT.sub("", body[match.end() : end]).strip()
    return found


def description_problems(body: str) -> list[str]:
    present = sections(body)
    problems = []
    for name in REQUIRED:
        text = present.get(name.casefold())
        if text is None:
            problems.append(f"no '## {name}' section")
        elif text.casefold() in PLACEHOLDERS:
            problems.append(f"the '## {name}' section is empty")
    return problems
