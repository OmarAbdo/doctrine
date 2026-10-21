"""Reads the last thing Claude said from a Claude Code transcript (JSON lines)."""

import json
from pathlib import Path


def message_text(entry: dict[str, object]) -> str:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def last_assistant_message(transcript_path: str | None) -> str:
    if not transcript_path or not Path(transcript_path).exists():
        return ""
    lines = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = message_text(entry) if entry.get("type") == "assistant" else ""
        if text.strip():
            return text
    return ""
