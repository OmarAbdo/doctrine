"""The decisions behind Claude Code's hooks: may this tool call run, and may this turn end?"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from doctrine.domain.governance.claims import success_claims
from doctrine.domain.safety.command_policy import CommandContext, judge_command
from doctrine.domain.safety.protected import is_protected
from doctrine.domain.governance.work_item import WorkItem

SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
FILE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
TEST_ROOT = "tests/"
COMMAND_OWNED = ("work/", "metrics/")


@dataclass(frozen=True)
class ToolEvent:
    tool: str
    tool_input: Mapping[str, Any]

    @property
    def file_path(self) -> str:
        return str(self.tool_input.get("file_path") or self.tool_input.get("notebook_path") or "")


@dataclass(frozen=True)
class Situation:
    """What the guard knows about the moment: the project (None outside one) and its state."""

    root: str | None
    source_roots: tuple[str, ...]
    branch: str
    item: WorkItem | None
    red_seen: bool
    line_stopped: bool
    unchecked_changes: bool

    def relative(self, path: str) -> str | None:
        if self.root is None:
            return None
        root, target = self.root.replace("\\", "/").rstrip("/") + "/", path.replace("\\", "/")
        if not target.lower().startswith(root.lower()):
            return None
        return target[len(root) :]

    def is_source(self, relative_path: str) -> bool:
        inside = any(
            relative_path.startswith(source.rstrip("/") + "/") for source in self.source_roots
        )
        return inside and not relative_path.startswith(TEST_ROOT)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""


ALLOW = Decision(allowed=True)


def refuse(reason: str) -> Decision:
    return Decision(allowed=False, reason=reason)


def item_refusal(relative: str, situation: Situation) -> str | None:
    """Why the active item may not change this project file, or None when it may."""
    item = situation.item
    if item is None:
        return "No active work item. Start one with `doctrine item start` before editing."
    if situation.line_stopped and item.kind != "restore":
        return (
            "The line is stopped: the outcome metric fell under its stop value. "
            "Only a restore item may change code until it recovers."
        )
    if not item.covers(relative):
        return (
            f"{relative} is outside item {item.id}'s scope {list(item.scope)}. "
            "Finish this item, or start one whose scope covers it."
        )
    if item.red_first and situation.is_source(relative) and not situation.red_seen:
        return (
            f"Item {item.id} is a {item.kind}: write a failing test first and run "
            "`doctrine test` so the red run is recorded."
        )
    return None


def decide_edit(path: str, situation: Situation) -> Decision:
    if is_protected(path):
        return refuse("doctrine's own files change only through an approved pull request.")
    relative = situation.relative(path)
    if relative is None:
        return ALLOW
    if relative.startswith(COMMAND_OWNED):
        return refuse(
            f"{relative} is written by doctrine commands only "
            "(`doctrine item`, `doctrine metric record`)."
        )
    reason = item_refusal(relative, situation)
    return ALLOW if reason is None else refuse(reason)


def decide_tool_use(event: ToolEvent, situation: Situation) -> Decision:
    if event.tool in SHELL_TOOLS:
        verdict = judge_command(
            str(event.tool_input.get("command", "")),
            CommandContext(current_branch=situation.branch, in_project=situation.root is not None),
        )
        return Decision(allowed=verdict.allowed, reason=verdict.reason)
    if event.tool in FILE_TOOLS:
        return decide_edit(event.file_path, situation)
    return ALLOW


def decide_stop(message: str, situation: Situation) -> Decision:
    claims = success_claims(message)
    if situation.root is None or not claims or not situation.unchecked_changes:
        return ALLOW
    return refuse(
        f"You claim {', '.join(sorted(set(claims)))}, but the changes since the last "
        "passing `doctrine check` are unchecked. Run `doctrine check`, or say plainly "
        "what isn't verified."
    )
