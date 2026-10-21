"""`doctrine item start|show|done` and `doctrine metric record`: one change at a time."""

import json
import subprocess
from pathlib import Path

from doctrine.adapters.cli.console import complain, load_project, say
from doctrine.adapters.storage.metric_log import append_metric
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.storage.evidence_log import EvidenceLog
from doctrine.adapters.storage.state_store import StateStore, now
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.domain.governance.evidence import item_not_ready
from doctrine.domain.governance.work_item import WorkItem, parse_work_item

METRIC_TIMEOUT_SECONDS = 600


def item_toml(item: WorkItem) -> str:
    scope = ", ".join(json.dumps(pattern) for pattern in item.scope)
    return (
        f"id = {json.dumps(item.id)}\ntitle = {json.dumps(item.title)}\n"
        f"kind = {json.dumps(item.kind)}\nscope = [{scope}]\n"
    )


def next_item_id(project: Project) -> str:
    """One more than any item in work/ or on any branch, so parallel items never share a number."""
    on_branches = GitRepository(project.root).highest_item_number()
    return str(max(int(project.next_item_id()), on_branches + 1))


def item_start(cwd: Path, kind: str, title: str, scope: list[str]) -> int:
    project = load_project(cwd)
    state = StateStore(project.root)
    if state.active_item():
        complain(
            f"Item {state.active_item()} is still active: finish it with `doctrine item done`."
        )
        return 1
    item = parse_work_item(
        {"id": next_item_id(project), "title": title, "kind": kind, "scope": scope}
    )
    (project.root / "work").mkdir(exist_ok=True)
    (project.root / "work" / f"{item.id}-{item.slug}.toml").write_text(
        item_toml(item), encoding="utf-8"
    )
    GitRepository(project.root).create_branch(item.branch)
    state.update(item=item.id, unchecked=False, stop_blocks=0)
    EvidenceLog(project.root).record("item", "started", detail=f"{item.kind}: {item.title}")
    say(f"Item {item.id} started on branch {item.branch}.")
    if item.red_first:
        say("Write a failing test first, then run `doctrine test` to record the red run.")
    return 0


def item_show(cwd: Path) -> int:
    project = load_project(cwd)
    item_id = StateStore(project.root).active_item()
    item = project.work_item(item_id) if item_id else None
    say(
        f"Item {item.id}: {item.title} ({item.kind}), scope {list(item.scope)}"
        if item
        else "No active item."
    )
    return 0


def item_done(cwd: Path) -> int:
    project = load_project(cwd)
    state = StateStore(project.root)
    item_id = state.active_item()
    item = project.work_item(item_id) if item_id else None
    if item is None:
        complain("No active item.")
        return 1
    if state.unchecked_changes():
        complain("Changes since the last passing `doctrine check`: run it first.")
        return 1
    log = EvidenceLog(project.root)
    reason = item_not_ready(log.entries(), item.id, red_first=item.red_first)
    if reason:
        complain(f"Item {item.id} isn't done: {reason}.")
        return 1
    log.record("item", "done")
    state.update(item=None)
    say(f"Item {item.id} is done here. Push {item.branch} and open a pull request; CI decides.")
    return 0


def metric_record(cwd: Path) -> int:
    project = load_project(cwd)
    outcome = project.contract.outcome
    finished = subprocess.run(
        list(outcome.command),
        cwd=project.root,
        capture_output=True,
        text=True,
        timeout=METRIC_TIMEOUT_SECONDS,
        check=False,
    )
    lines = finished.stdout.strip().splitlines()
    if finished.returncode != 0 or not lines:
        complain(f"The metric command failed: {finished.stderr.strip()[:500]}")
        return 1
    value = float(lines[-1])
    append_metric(project.root, value, now())
    EvidenceLog(project.root).record("metric", f"{value:g}", detail=outcome.metric)
    stopped = " LINE STOPPED." if outcome.line_stopped(value) else ""
    say(f"{outcome.metric}: {value:g} (stops below {outcome.stop_value:g}).{stopped}")
    return 0
