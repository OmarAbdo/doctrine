"""`doctrine eval run <task>`: an AI task on its eval set, recorded for its prompt and eval set."""

from pathlib import Path

from doctrine.adapters.cli.console import complain, load_project, say
from doctrine.adapters.storage.eval_files import EvalFiles
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.storage.state_store import now
from doctrine.adapters.tools.project_environment import project_command
from doctrine.adapters.tools.task_command import TaskCommand
from doctrine.application.evals import record_eval_run
from doctrine.domain.evals.task import AiTask


def find_task(project: Project, name: str) -> AiTask | None:
    tasks = {task.name: task for task in project.contract.ai_tasks}
    if name not in tasks:
        known = ", ".join(sorted(tasks)) or "none"
        complain(f"There is no AI task {name}; the contract has: {known}.")
    return tasks.get(name)


def eval_run(cwd: Path, name: str) -> int:
    project = load_project(cwd)
    task = find_task(project, name)
    if task is None:
        return 1
    command = TaskCommand(project.root, *project_command(project, task.command))
    result = record_eval_run(EvalFiles(project.root, task), command, now(), judge=task.judge)
    failed = f"; failed: {', '.join(result.failures)}" if result.failures else ""
    say(f"{name}: {result.score:g} on {result.total} cases (minimum {task.minimum:g}){failed}.")
    say(f"Recorded in {task.results}; commit it with the prompt or eval set it measured.")
    if result.score < task.minimum:
        complain(f"{name} scores under the minimum: the pull request will be refused.")
        return 1
    return 0
