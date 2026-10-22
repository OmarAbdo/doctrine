"""The workflows a new project gets from `doctrine init`, read as text."""

from pathlib import Path


def triggers(project: Path, workflow: str) -> str:
    text = (project / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
    return text.split("\non:", 1)[1].split("\npermissions:", 1)[0].split("\njobs:", 1)[0]


def test_a_new_projects_approval_re_runs_its_failed_check(project: Path) -> None:
    """Doctrine's own repository learnt this on 2026-10-22 (#15): a review that starts a second
    run leaves the first one red, and branch protection counts both."""
    assert "pull_request_review" not in triggers(project, "doctrine.yml")
    approval = (project / ".github" / "workflows" / "doctrine-approval.yml").read_text(
        encoding="utf-8"
    )
    assert "pull_request_review" in triggers(project, "doctrine-approval.yml")
    assert "github.event.review.state == 'approved'" in approval
    assert "--workflow doctrine.yml" in approval
    assert "gh run rerun" in approval
