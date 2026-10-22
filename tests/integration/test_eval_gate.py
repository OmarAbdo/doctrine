"""`doctrine ci evals` on a real repository: a changed prompt needs a recorded run that holds up."""

import json
import sys
from pathlib import Path

import pytest
from support.projects import commit_all, git, write

from doctrine.adapters.cli.gates import eval_gate
from doctrine.adapters.storage.eval_files import EvalFiles
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.task_command import TaskCommand
from doctrine.application.evals import record_eval_run

RIGHT = "import json, sys\nprint(json.load(sys.stdin)['text'] * 2)\n"
# Doubles "a" only.
HALF_RIGHT = (
    "import json, sys\ntext = json.load(sys.stdin)['text']\n"
    "print(text * 2 if text == 'a' else text)\n"
)
CASES = [
    {"id": "a", "input": {"text": "a"}, "expected": "aa"},
    {"id": "b", "input": {"text": "b"}, "expected": "bb"},
]


def task_on_main(project: Path) -> None:
    command = json.dumps([sys.executable, "tasks/shout.py"])
    task = '\n[[ai_tasks]]\nname = "shout"\nprompt = "prompts/shout.md"\n'
    task += f"command = {command}\nminimum = 0.5\n"
    contract = project / "doctrine.toml"
    contract.write_text(contract.read_text(encoding="utf-8") + task, encoding="utf-8")
    write(project, "tasks/shout.py", RIGHT)
    write(project, "prompts/shout.md", "Shout.\n")
    write(project, "evals/shout/cases.jsonl", "".join(json.dumps(case) + "\n" for case in CASES))
    run_eval(project)
    commit_all(project, "The shout task, scoring 1")
    git(project, "switch", "-q", "-c", "item/1-shout-better")


def run_eval(project: Path) -> None:
    task = Project.load(project).contract.ai_tasks[0]
    files, command = EvalFiles(project, task), TaskCommand(project, task.command)
    record_eval_run(files, command, "2026-10-22T19:00:00Z")


def test_untouched_prompts_and_eval_sets_pass(project: Path) -> None:
    task_on_main(project)
    assert eval_gate.evals_command(project, "main") == 0


def test_a_changed_prompt_needs_a_run_on_the_new_version(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task_on_main(project)
    write(project, "prompts/shout.md", "Shout louder.\n")
    commit_all(project, "A new prompt")
    assert eval_gate.evals_command(project, "main") == 1
    assert "run `doctrine eval run shout`" in capsys.readouterr().err
    run_eval(project)
    commit_all(project, "Its run")
    assert eval_gate.evals_command(project, "main") == 0


def test_a_lower_score_on_the_same_eval_set_waits_for_the_approver(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_on_main(project)
    write(project, "prompts/shout.md", "Repeat.\n")
    write(project, "tasks/shout.py", HALF_RIGHT)
    run_eval(project)
    commit_all(project, "A cheaper prompt, scoring 0.5")
    monkeypatch.setattr(eval_gate, "owner_approved", lambda environment, approver: False)
    assert eval_gate.evals_command(project, "main") == 1
    monkeypatch.setattr(eval_gate, "owner_approved", lambda environment, approver: True)
    assert eval_gate.evals_command(project, "main") == 0
