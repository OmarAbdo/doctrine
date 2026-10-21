import io
import json
from pathlib import Path

import pytest
from support.projects import write

from doctrine.adapters.claude import edit_review, hooks, situation, stop_gate, transcript
from doctrine.adapters.storage.evidence_log import EvidenceLog
from doctrine.adapters.storage.state_store import StateStore


def hook(
    name: str,
    event: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str, str]:
    stream = io.TextIOWrapper(io.BytesIO(json.dumps(event).encode("utf-8")), encoding="utf-8")
    monkeypatch.setattr("sys.stdin", stream)
    code = hooks.run_hook(name)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_a_skipped_hook_is_refused_everywhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    event = {
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "git commit --no-verify -m quick"},
    }
    code, out, _ = hook("pre-tool-use", event, monkeypatch, capsys)
    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_an_edit_without_an_item_is_refused_in_a_project(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = project / "src" / "sample_jobs" / "domain" / "job.py"
    event = {"cwd": str(project), "tool_name": "Write", "tool_input": {"file_path": str(target)}}
    _, out, _ = hook("pre-tool-use", event, monkeypatch, capsys)
    assert (
        "doctrine item start" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_the_session_starts_with_the_project_brief(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out, _ = hook("session-start", {"cwd": str(project)}, monkeypatch, capsys)
    assert (
        "Doctrine project Sample Jobs" in json.loads(out)["hookSpecificOutput"]["additionalContext"]
    )


def test_a_changed_file_with_problems_goes_straight_back_to_claude(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = write(project, "src/sample_jobs/domain/job.py", "tmp = 1\n")
    event = {"cwd": str(project), "tool_name": "Write", "tool_input": {"file_path": str(bad)}}
    code, _, err = hook("post-tool-use", event, monkeypatch, capsys)
    assert code == hooks.BLOCK_EXIT
    assert "'tmp' uses the abbreviation 'tmp'" in err
    assert StateStore(project).unchecked_changes()
    assert edit_review.review_edit(project.parent / "elsewhere.py") == []


def test_a_claim_over_unchecked_changes_is_sent_back_then_let_go_after_three_tries(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    StateStore(project).update(unchecked=True)
    event = {"cwd": str(project), "last_assistant_message": "Tidy titles works now."}
    for _ in range(stop_gate.STOP_BLOCK_LIMIT):
        _, out, _ = hook("stop", event | {"stop_hook_active": True}, monkeypatch, capsys)
        assert json.loads(out)["decision"] == "block"
    code, out, _ = hook("stop", event | {"stop_hook_active": True}, monkeypatch, capsys)
    assert (code, out) == (0, "")
    assert EvidenceLog(project).entries()[-1].outcome == "overridden"


def test_the_last_assistant_message_is_read_from_the_transcript(tmp_path: Path) -> None:
    lines = [
        {"type": "user", "message": {"content": "go"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "It works."}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
    ]
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    assert transcript.last_assistant_message(str(path)) == "It works."
    assert transcript.last_assistant_message(None) == ""


def test_outside_a_project_the_situation_has_no_root(tmp_path: Path) -> None:
    assert situation.situation_for(tmp_path).root is None
    assert situation.status_for(tmp_path) is None


def test_an_honest_turn_end_resets_the_refusal_count(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    StateStore(project).update(unchecked=True, stop_blocks=2)
    event = {
        "cwd": str(project),
        "last_assistant_message": "The check failed; nothing is verified.",
    }
    code, out, _ = hook("stop", event, monkeypatch, capsys)
    assert (code, out) == (0, "")
    assert StateStore(project).load()["stop_blocks"] == 0
