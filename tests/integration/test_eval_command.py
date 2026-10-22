"""`doctrine eval run <task>` on a real project."""

import json
import sys
from pathlib import Path

import pytest
from support.projects import write

from doctrine.adapters.cli.commands import eval_command
from doctrine.adapters.cli.main import main

ANSWER = "import json, sys\nprint(json.load(sys.stdin)['text'].upper())\n"
CASES = [
    {"id": "hello", "input": {"text": "hello"}, "expected": "HELLO"},
    {"id": "wrong", "input": {"text": "bye"}, "expected": "GOODBYE"},
]


def add_task(project: Path, minimum: float) -> None:
    command = json.dumps([sys.executable, "tasks/shout.py"])
    task = '\n[[ai_tasks]]\nname = "shout"\nprompt = "prompts/shout.md"\n'
    task += f"command = {command}\nminimum = {minimum}\n"
    contract = project / "doctrine.toml"
    contract.write_text(contract.read_text(encoding="utf-8") + task, encoding="utf-8")
    write(project, "tasks/shout.py", ANSWER)
    write(project, "prompts/shout.md", "Shout the text back.\n")
    write(project, "evals/shout/cases.jsonl", "".join(json.dumps(case) + "\n" for case in CASES))


def recorded(project: Path) -> list[dict[str, object]]:
    lines = (project / "evals/shout/results.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_a_run_is_recorded_and_judged_against_the_minimum(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    add_task(project, minimum=0.5)
    monkeypatch.chdir(project)
    assert main(["eval", "run", "shout"]) == 0
    assert "shout: 0.5 on 2 cases (minimum 0.5); failed: wrong" in capsys.readouterr().out
    assert [line["score"] for line in recorded(project)] == [0.5]


def test_a_run_under_the_minimum_fails_but_is_still_recorded(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    add_task(project, minimum=0.9)
    monkeypatch.chdir(project)
    assert main(["eval", "run", "shout"]) == 1
    assert "under the minimum" in capsys.readouterr().err
    assert len(recorded(project)) == 1


def test_an_unknown_task_is_named_with_the_known_ones(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    add_task(project, minimum=0.5)
    assert eval_command.eval_run(project, "whisper") == 1
    assert "no AI task whisper; the contract has: shout" in capsys.readouterr().err
