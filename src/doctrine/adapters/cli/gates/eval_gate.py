"""`doctrine ci evals`: a pull request that changes an AI task's prompt or eval set brings a
recorded run on the new version that holds the task's minimum; a lower score than before on the
same eval set waits for the approver."""

import json
import os
from pathlib import Path

from doctrine.adapters.cli.console import complain, load_project, say
from doctrine.adapters.cli.gates.ci_commands import approver_at
from doctrine.adapters.cli.gates.github_reviews import owner_approved
from doctrine.adapters.storage.eval_files import EvalFiles
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.domain.evals.results import EvalResult, EvalVerdict, eval_problems, parse_results
from doctrine.domain.evals.task import AiTask


def changed_tasks(project: Project, git: GitRepository, base: str) -> list[AiTask]:
    changed = set(git.changed_files(base))
    return [task for task in project.contract.ai_tasks if {task.prompt, task.cases} & changed]


def results_at(git: GitRepository, base: str, task: AiTask) -> list[EvalResult]:
    lines = (git.file_at(base, task.results) or "").splitlines()
    return parse_results(json.loads(line) for line in lines if line.strip())


def verdict_on(project: Project, base: str) -> EvalVerdict:
    git, verdict = GitRepository(project.root), EvalVerdict()
    for task in changed_tasks(project, git, base):
        files = EvalFiles(project.root, task)
        found = eval_problems(task, files.version(), files.results(), results_at(git, base, task))
        verdict.refusals.extend(found.refusals)
        verdict.approvals.extend(found.approvals)
    return verdict


def evals_command(cwd: Path, base: str) -> int:
    project = load_project(cwd)
    verdict = verdict_on(project, base)
    for refusal in verdict.refusals:
        complain(refusal)
    if verdict.refusals:
        return 1
    if not verdict.approvals:
        say("Every changed prompt and eval set has a recorded run that holds its minimum.")
        return 0
    scores = "\n".join(f"  {score}" for score in verdict.approvals)
    say(f"Scores that need Omar's approval:\n{scores}")
    if owner_approved(os.environ, approver_at(project, base)):
        say("Approved by the owner on this commit.")
        return 0
    complain("Not approved yet: the merge waits for the owner's approval of this commit.")
    return 1
