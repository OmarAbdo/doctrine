"""Claude Code hook entry points: `doctrine hook <event>` reads the event as JSON on stdin.

Refusals go back to Claude with the reason, so the next step is the right one, not a retry.
"""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from doctrine.adapters.claude.edit_review import review_edit
from doctrine.adapters.claude.situation import situation_for, status_for
from doctrine.adapters.claude.stop_gate import stop_refusal
from doctrine.adapters.storage.project_files import CONTRACT_FILE
from doctrine.application.brief import session_brief
from doctrine.application.guard import FILE_TOOLS, ToolEvent, decide_tool_use

BLOCK_EXIT = 2


def emit(payload: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(payload))
    return 0


def denial(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Doctrine: {reason}",
        }
    }


def pre_tool_use(event: dict[str, Any]) -> int:
    tool = ToolEvent(tool=event.get("tool_name", ""), tool_input=event.get("tool_input") or {})
    try:
        decision = decide_tool_use(tool, situation_for(Path(event.get("cwd") or ".")))
    except (OSError, ValueError, KeyError) as error:
        if tool.file_path.endswith(CONTRACT_FILE):
            return 0
        reason = f"doctrine could not read the project ({error}); fix {CONTRACT_FILE} first."
        return emit(denial(reason))
    return 0 if decision.allowed else emit(denial(decision.reason))


def post_tool_use(event: dict[str, Any]) -> int:
    if event.get("tool_name") not in FILE_TOOLS:
        return 0
    path = Path(ToolEvent(event["tool_name"], event.get("tool_input") or {}).file_path)
    problems = review_edit(path)
    if not problems:
        return 0
    header = "Doctrine found problems in the file you just changed; fix them now:"
    sys.stderr.write("\n".join([header, *problems]) + "\n")
    return BLOCK_EXIT


def stop(event: dict[str, Any]) -> int:
    reason = stop_refusal(event)
    return 0 if reason is None else emit({"decision": "block", "reason": f"Doctrine: {reason}"})


def session_start(event: dict[str, Any]) -> int:
    text = session_brief(status_for(Path(event.get("cwd") or ".")))
    context = {"hookEventName": "SessionStart", "additionalContext": text}
    return emit({"hookSpecificOutput": context})


HANDLERS: dict[str, Callable[[dict[str, Any]], int]] = {
    "pre-tool-use": pre_tool_use,
    "post-tool-use": post_tool_use,
    "stop": stop,
    "session-start": session_start,
}


def run_hook(name: str) -> int:
    event = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    return HANDLERS[name](event)
