"""An AI task run on its eval set: the task's command answers each case, the run is recorded."""

import json
import sys
from pathlib import Path

from support.projects import write

from doctrine.adapters.storage.eval_files import EvalFiles
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.task_command import TaskCommand
from doctrine.application.evals import record_eval_run

# Answers in capitals, and crashes on the input "crash".
ANSWER = (
    "import json, sys\n"
    "text = json.load(sys.stdin)['text']\n"
    "if text == 'crash':\n    raise SystemExit(3)\n"
    "print(text.upper())\n"
)
CASES = [
    {"id": "hello", "input": {"text": "hello"}, "expected": "HELLO"},
    {"id": "wrong", "input": {"text": "bye"}, "expected": ["GOODBYE", "SEE YOU"]},
    {"id": "crash", "input": {"text": "crash"}, "expected": "CRASH"},
]


def with_task(project: Path) -> Project:
    command = json.dumps([sys.executable, "tasks/shout.py"])
    task = '\n[[ai_tasks]]\nname = "shout"\nprompt = "prompts/shout.md"\n'
    task += f"command = {command}\nminimum = 0.5\n"
    contract = project / "doctrine.toml"
    contract.write_text(contract.read_text(encoding="utf-8") + task, encoding="utf-8")
    write(project, "tasks/shout.py", ANSWER)
    write(project, "prompts/shout.md", "Shout the text back.\n")
    write(project, "evals/shout/cases.jsonl", "".join(json.dumps(case) + "\n" for case in CASES))
    return Project.load(project)


def test_a_run_scores_the_answers_and_is_recorded(project: Path) -> None:
    loaded = with_task(project)
    task = loaded.contract.ai_tasks[0]
    files = EvalFiles(project, task)
    result = record_eval_run(files, TaskCommand(project, task.command), "2026-10-22T16:00:00Z")
    assert (result.total, result.failures) == (3, ("wrong", "crash"))
    assert result.score == 1 / 3
    assert files.results() == [result]
    assert (result.prompt, result.cases) == (files.version().prompt, files.version().cases)


def test_versions_change_with_content_but_not_with_line_endings(project: Path) -> None:
    files = EvalFiles(project, with_task(project).contract.ai_tasks[0])
    before = files.version()
    (project / "prompts/shout.md").write_bytes(b"Shout the text back.\r\n")
    assert files.version() == before
    write(project, "prompts/shout.md", "Whisper the text back.\n")
    assert files.version().prompt != before.prompt
    assert files.version().cases == before.cases
