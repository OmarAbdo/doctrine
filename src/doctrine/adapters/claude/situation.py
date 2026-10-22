"""Builds the guard's view of the moment from the project on disk."""

from pathlib import Path

from doctrine.adapters.storage.metric_log import latest_metric, metric_values
from doctrine.adapters.storage.project_files import Project, find_root
from doctrine.adapters.storage.evidence_log import EvidenceLog
from doctrine.adapters.storage.state_store import StateStore
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.application.brief import ProjectStatus
from doctrine.application.guard import Situation


def outside_project(cwd: Path) -> Situation:
    return Situation(
        root=None,
        source_roots=(),
        branch=GitRepository(cwd).current_branch(),
        item=None,
        red_seen=False,
        line_stopped=False,
        unchecked_changes=False,
    )


def situation_for(cwd: Path) -> Situation:
    root = find_root(cwd)
    if root is None:
        return outside_project(cwd)
    project, state = Project.load(root), StateStore(root)
    item_id = state.active_item()
    item = project.work_item(item_id) if item_id else None
    values = metric_values(root)
    return Situation(
        root=str(root),
        source_roots=tuple(service.path for service in project.contract.services),
        branch=GitRepository(root).current_branch(),
        item=item,
        red_seen=item is not None and EvidenceLog(root).red_seen(item.id),
        line_stopped=project.contract.outcome.line_stopped(values),
        unchecked_changes=state.unchecked_changes(),
    )


def status_for(cwd: Path) -> ProjectStatus | None:
    root = find_root(cwd)
    if root is None:
        return None
    project, state = Project.load(root), StateStore(root)
    item_id = state.active_item()
    item = project.work_item(item_id) if item_id else None
    outcome = project.contract.outcome
    return ProjectStatus(
        name=project.contract.name,
        metric=outcome.metric,
        latest=latest_metric(root),
        stop_value=outcome.stop_value,
        launched=outcome.launched(metric_values(root)),
        item=f"{item.id} {item.title} ({item.kind})" if item else None,
        branch=GitRepository(root).current_branch(),
    )
