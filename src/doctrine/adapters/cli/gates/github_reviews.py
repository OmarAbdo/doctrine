"""Whether the approver approved the pull request's current commit, asked from GitHub in CI."""

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

TIMEOUT_SECONDS = 60


def pull_request(environment: Mapping[str, str]) -> tuple[int, str] | None:
    """(number, head commit) of the pull request this CI run is for, or None outside one."""
    event_path = environment.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    request = event.get("pull_request")
    return (int(request["number"]), str(request["head"]["sha"])) if request else None


def pull_request_branch(environment: Mapping[str, str]) -> str:
    """The pull request's own branch from the event, which every pull request event carries
    (GITHUB_HEAD_REF is empty when an approval starts the run)."""
    event_path = environment.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return ""
    request = json.loads(Path(event_path).read_text(encoding="utf-8")).get("pull_request") or {}
    return str(request.get("head", {}).get("ref", ""))


def reviews(repository: str, number: int) -> list[dict[str, Any]]:
    finished = subprocess.run(
        ["gh", "api", f"repos/{repository}/pulls/{number}/reviews", "--paginate"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    return json.loads(finished.stdout) if finished.returncode == 0 and finished.stdout else []


def owner_approved(environment: Mapping[str, str], approver: str) -> bool:
    request = pull_request(environment)
    repository = environment.get("GITHUB_REPOSITORY", "")
    if request is None or not repository or not approver:
        return False
    number, head = request
    return any(
        review.get("state") == "APPROVED"
        and str((review.get("user") or {}).get("login", "")).lower() == approver.lower()
        and review.get("commit_id") == head
        for review in reviews(repository, number)
    )
