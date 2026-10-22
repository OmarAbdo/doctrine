"""Doctrine's own GitHub workflows, read as text (no YAML parser among the pinned tools)."""

from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def triggers(workflow: str) -> str:
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    return text.split("\non:", 1)[1].split("\npermissions:", 1)[0]


def test_one_check_per_commit_an_approval_starts_no_second_run() -> None:
    """2026-10-22: a review started a second "self" run; the first, failed before the approval,
    stayed red and branch protection refused the merge of #13 until it was re-run."""
    assert "pull_request_review" not in triggers("self.yml")


def test_an_approval_re_runs_the_failed_check_of_the_approved_commit() -> None:
    approval = (WORKFLOWS / "approval.yml").read_text(encoding="utf-8")
    assert "pull_request_review" in triggers("approval.yml")
    assert "github.event.review.state == 'approved'" in approval
    assert "gh run rerun" in approval
    assert "--commit" in approval
