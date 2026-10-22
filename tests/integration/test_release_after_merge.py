"""2026-10-22 (#48): release.yml never ran. merge.yml merges with the repository's own token, and
GitHub starts no workflow for a push made with that token, so `on: push` alone never fired."""

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"


def test_a_finished_merge_workflow_starts_the_tagging() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    triggers = text.split("\non:", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_run:" in triggers
    assert "workflows: [merge]" in triggers
    assert "ref: main" in text
