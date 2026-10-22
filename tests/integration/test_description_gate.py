"""Each item's tests in a file of their own: two items appending to one file conflict (#19, #20)."""

import json
from pathlib import Path

import pytest

from doctrine.adapters.cli import main


def test_the_description_gate_reads_the_pull_request_from_github(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = tmp_path / "event.json"
    body = "## What changed\nx\n## Why\ny\n## Proof\nz\n## Not verified\nnothing\n"
    event.write_text(json.dumps({"pull_request": {"number": 7, "body": body}}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert main.description_command() == 0
    event.write_text(json.dumps({"pull_request": {"number": 7, "body": None}}))
    assert main.description_command() == 1
