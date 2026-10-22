"""`doctrine ci description`: the pull request says what changed, why, the proof and what is not
verified, so a reviewer reads one short page and nothing unproven hides in it."""

import json
import os
from pathlib import Path

from doctrine.adapters.cli.console import complain, say
from doctrine.domain.governance.description import REQUIRED, description_problems


def description_command() -> int:
    """The description of the pull request in GitHub's event, judged section by section."""
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH") or "missing-event.json")
    event = json.loads(event_path.read_text(encoding="utf-8")) if event_path.exists() else {}
    problems = description_problems(str((event.get("pull_request") or {}).get("body") or ""))
    for problem in problems:
        complain(f"Pull request description: {problem}.")
    if problems:
        complain(f"It needs these sections: {', '.join(f'## {name}' for name in REQUIRED)}.")
        return 1
    say("The description says what changed, why, the proof and what is not verified.")
    return 0
