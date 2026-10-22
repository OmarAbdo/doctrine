"""`doctrine eval label <judge> --traces <file>`: the labelling page, opened in the browser."""

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from support.projects import write

from doctrine.adapters.cli.commands import label_command
from doctrine.adapters.cli.main import main
from doctrine.adapters.web.label_page import LabelSession, label_server


def add_judge(project: Path, judge: bool) -> None:
    task = '\n[[ai_tasks]]\nname = "fit-judge"\nprompt = "prompts/judge.md"\n'
    task += f'command = ["python", "judge.py"]\nminimum = 0.8\njudge = {str(judge).lower()}\n'
    contract = project / "doctrine.toml"
    contract.write_text(contract.read_text(encoding="utf-8") + task, encoding="utf-8")
    trace = {"id": "t1", "input": "Python role", "output": "fits"}
    write(project, "traces/fit.jsonl", json.dumps(trace) + "\n")


def test_the_page_opens_in_the_browser_with_the_first_trace(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    add_judge(project, judge=True)
    servers: list[ThreadingHTTPServer] = []
    pages: list[str] = []

    def keep(session: LabelSession, port: int) -> ThreadingHTTPServer:
        servers.append(label_server(session, port))
        return servers[0]

    def browse(url: str) -> bool:
        def read_then_stop() -> None:
            with urllib.request.urlopen(url, timeout=10) as response:
                pages.append(response.read().decode("utf-8"))
            servers[0].shutdown()

        threading.Thread(target=read_then_stop, daemon=True).start()
        return True

    monkeypatch.setattr(label_command, "label_server", keep)
    monkeypatch.setattr(label_command.webbrowser, "open", browse)
    monkeypatch.chdir(project)
    assert main(["eval", "label", "fit-judge", "--traces", "traces/fit.jsonl"]) == 0
    assert "Python role" in pages[0]


def test_only_a_judge_gets_labels(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add_judge(project, judge=False)
    assert label_command.eval_label(project, "fit-judge", Path("traces/fit.jsonl")) == 1
    assert "mark it judge = true" in capsys.readouterr().err


def test_a_missing_traces_file_is_named(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add_judge(project, judge=True)
    assert label_command.eval_label(project, "fit-judge", Path("traces/none.jsonl")) == 1
    assert "traces/none.jsonl" in capsys.readouterr().err.replace("\\", "/")
