import json
from pathlib import Path

import pytest
from support.projects import write

from doctrine.adapters.storage.evidence_log import EvidenceLog, TamperedLogError
from doctrine.adapters.storage.metric_log import append_metric, latest_metric
from doctrine.adapters.storage.project_files import Project, find_root
from doctrine.adapters.storage.state_store import StateStore


def test_the_project_is_found_from_any_folder_inside_it(project: Path) -> None:
    assert find_root(project / "src" / "sample_jobs" / "domain") == project
    assert find_root(project.parent) is None


def test_the_contract_and_the_rule_table_load(project: Path) -> None:
    loaded = Project.load(project)
    assert loaded.contract.name == "Sample Jobs"
    assert loaded.contract.services[0].path == "src/sample_jobs"
    assert loaded.rules.limit("function_lines") == 40


def test_the_sources_of_a_service_are_read_by_path(project: Path) -> None:
    write(project, "src/sample_jobs/domain/job.py", "TITLE = 'x'\n")
    write(project, "tests/unit/test_job.py", "from sample_jobs.domain.job import TITLE\n")
    loaded = Project.load(project)
    sources = loaded.sources(loaded.contract.services[0])
    assert "sample_jobs/domain/job.py" in sources.modules
    assert "tests/unit/test_job.py" in sources.tests


def test_the_state_keeps_the_active_item_and_unchecked_changes(project: Path) -> None:
    state = StateStore(project)
    state.update(item="3", unchecked=True)
    assert StateStore(project).active_item() == "3"
    assert StateStore(project).unchecked_changes()


def test_evidence_is_chained_and_a_hand_edit_is_caught(project: Path) -> None:
    log = EvidenceLog(project)
    StateStore(project).update(item="3")
    log.record("test", "red")
    log.record("test", "green")
    assert log.red_seen("3")
    entries = log.path.read_text(encoding="utf-8").splitlines()
    forged = json.loads(entries[0]) | {"outcome": "green"}
    log.path.write_text("\n".join([json.dumps(forged), entries[1]]) + "\n", encoding="utf-8")
    with pytest.raises(TamperedLogError):
        log.record("check", "passed")


def test_the_metric_history_returns_the_latest_value(project: Path) -> None:
    assert latest_metric(project) is None
    append_metric(project, 4.0, "2026-10-21T10:00:00Z")
    append_metric(project, 6.5, "2026-10-21T11:00:00Z")
    assert latest_metric(project) == 6.5
