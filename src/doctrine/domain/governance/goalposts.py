"""Changes to a project's goalposts that need Omar's approval: anything that makes the rules looser.

Tightening a limit and adding eval cases are free. Everything listed here blocks the merge until he
approves the pull request.
"""

from collections.abc import Mapping, Sequence

from doctrine.domain.governance.contract import Contract, Outcome
from doctrine.domain.rules.table import RuleTable


def limit_changes(before: Contract, after: Contract, table: RuleTable) -> list[str]:
    changes = []
    for name, value in before.limits.items():
        if name not in after.limits:
            changes.append(f"limit {name}: {value} -> rule table")
            continue
        wanted, current = (
            table.limits[name].with_value(after.limits[name]),
            table.limits[name].with_value(value),
        )
        if wanted.is_looser_than(current):
            changes.append(f"limit {name}: {value} -> {after.limits[name]}")
    return changes


def exception_changes(before: Contract, after: Contract) -> list[str]:
    return [
        f"exception added to {kind}: {entry}"
        for kind, entries in after.exceptions.items()
        for entry in entries
        if entry not in before.allowed(kind)
    ]


def outcome_changes(before: Outcome, after: Outcome) -> list[str]:
    changes = []
    if after.metric != before.metric:
        changes.append(f"outcome metric: {before.metric} -> {after.metric}")
    if after.command != before.command:
        changes.append("outcome command changed")
    if after.baseline < before.baseline:
        changes.append(f"outcome baseline: {before.baseline:g} -> {after.baseline:g}")
    if after.stop_below < before.stop_below:
        changes.append(f"outcome stop_below: {before.stop_below:g} -> {after.stop_below:g}")
    return changes


def service_changes(before: Contract, after: Contract) -> list[str]:
    old = {service.name: service for service in before.services}
    changes = []
    for service in after.services:
        previous = old.get(service.name)
        if previous and previous.architecture != service.architecture:
            changes.append(
                f"service {service.name}: architecture "
                f"{previous.architecture} -> {service.architecture}"
            )
        if previous and previous.profile != service.profile:
            changes.append(
                f"service {service.name}: profile {previous.profile} -> {service.profile}"
            )
    return changes


def ai_task_changes(before: Contract, after: Contract) -> list[str]:
    now = {task.name: task for task in after.ai_tasks}
    changes = []
    for task in before.ai_tasks:
        current = now.get(task.name)
        if current is None:
            changes.append(f"ai task {task.name} removed")
        elif current.minimum < task.minimum:
            changes.append(f"ai task {task.name}: minimum {task.minimum:g} -> {current.minimum:g}")
        elif task.judge and not current.judge:
            changes.append(f"ai task {task.name}: no longer a judge")
    return changes


def contract_changes(before: Contract, after: Contract, table: RuleTable) -> list[str]:
    changes = []
    if after.doctrine_version != before.doctrine_version:
        changes.append(f"doctrine version: {before.doctrine_version} -> {after.doctrine_version}")
    if after.approver != before.approver:
        changes.append(f"approver: {before.approver} -> {after.approver}")
    changes += limit_changes(before, after, table)
    changes += exception_changes(before, after)
    changes += outcome_changes(before.outcome, after.outcome)
    changes += ai_task_changes(before, after)
    return changes + service_changes(before, after)


def eval_label_changes(
    before: Sequence[Mapping[str, str]], after: Sequence[Mapping[str, str]]
) -> list[str]:
    now = {case["id"]: case["label"] for case in after}
    changes = []
    for case in before:
        if case["id"] not in now:
            changes.append(f"eval case {case['id']} removed")
        elif now[case["id"]] != case["label"]:
            changes.append(f"eval case {case['id']}: label {case['label']} -> {now[case['id']]}")
    return changes
