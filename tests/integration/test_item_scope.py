"""`doctrine item scope`: the one way to widen the active item's scope, visible in its work file."""

from pathlib import Path

import pytest

from doctrine.adapters.cli.commands.item_commands import item_scope, item_start
from doctrine.adapters.storage.evidence_log import EvidenceLog
from doctrine.adapters.storage.project_files import Project


def test_the_active_items_scope_grows_and_the_change_is_recorded(project: Path) -> None:
    assert item_start(project, "feature", "Fit score", ["src/sample_jobs/domain/**"]) == 0
    assert item_scope(project, ["src/sample_jobs/adapters/fit.py"]) == 0
    item = Project.load(project).work_item("1")
    assert item is not None
    assert item.scope == ("src/sample_jobs/domain/**", "src/sample_jobs/adapters/fit.py")
    text = (project / "work" / f"1-{item.slug}.toml").read_bytes()
    assert b"\r\n" not in text
    assert any(entry.outcome == "scope widened" for entry in EvidenceLog(project).entries())


def test_without_an_active_item_there_is_nothing_to_widen(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert item_scope(project, ["src/**"]) == 1
    assert "No active item" in capsys.readouterr().err


def test_everything_is_still_no_scope(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert item_start(project, "chore", "Tidy", ["src/sample_jobs/domain/**"]) == 0
    assert item_scope(project, ["**"]) == 1
    assert "names a folder or file" in capsys.readouterr().err
