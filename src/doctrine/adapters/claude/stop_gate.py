"""The end of a turn: a success claim over unchecked changes sends Claude back to work.

After STOP_BLOCK_LIMIT refusals in a row the turn may end, and the override is recorded as
evidence, so a loop never traps the session and the record still shows what happened.
"""

from pathlib import Path
from typing import Any

from doctrine.adapters.claude.situation import situation_for
from doctrine.adapters.claude.transcript import last_assistant_message
from doctrine.adapters.storage.evidence_log import EvidenceLog
from doctrine.adapters.storage.project_files import find_root
from doctrine.adapters.storage.state_store import StateStore
from doctrine.application.guard import decide_stop

STOP_BLOCK_LIMIT = 3


def final_message(event: dict[str, Any]) -> str:
    message = event.get("last_assistant_message")
    return str(message) if message else last_assistant_message(event.get("transcript_path"))


def stop_refusal(event: dict[str, Any]) -> str | None:
    """Why the turn may not end yet, or None when it may."""
    cwd = Path(event.get("cwd") or ".")
    decision = decide_stop(final_message(event), situation_for(cwd))
    root = find_root(cwd)
    if decision.allowed or root is None:
        return None
    state = StateStore(root)
    blocks = int(str(state.load().get("stop_blocks", 0))) + 1
    if event.get("stop_hook_active") and blocks > STOP_BLOCK_LIMIT:
        state.update(stop_blocks=0)
        EvidenceLog(root).record("stop", "overridden", detail=decision.reason)
        return None
    state.update(stop_blocks=blocks)
    return decision.reason
