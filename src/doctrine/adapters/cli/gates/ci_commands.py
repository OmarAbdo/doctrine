"""The checks CI runs on every pull request; they judge the committed result, not the session."""

import json
import os
import tomllib
from pathlib import Path

from doctrine.adapters.cli.console import complain, load_project, say
from doctrine.adapters.cli.gates.github_reviews import owner_approved, pull_request_branch
from doctrine.adapters.cli.gates.red_first import tests_fail_on_base
from doctrine.adapters.storage.project_files import CONTRACT_FILE, Project
from doctrine.adapters.tools.git_repository import GitRepository
from doctrine.domain.governance.contract import parse_contract
from doctrine.domain.governance.goalposts import contract_changes, eval_label_changes
from doctrine.domain.governance.work_item import WorkItem

GUARDED_FILES = (".github/", "CODEOWNERS", "rules/", "policy/")


def eval_changes(git: GitRepository, base: str, changed: list[str]) -> list[str]:
    changes = []
    for path in (path for path in changed if path.startswith("evals/") and path.endswith(".jsonl")):
        before = git.file_at(base, path) or ""
        after_path = git.root / path
        after = after_path.read_text(encoding="utf-8") if after_path.exists() else ""
        rows = [
            [json.loads(line) for line in text.splitlines() if line.strip()]
            for text in (before, after)
        ]
        changes += [f"{path}: {change}" for change in eval_label_changes(rows[0], rows[1])]
    return changes


def goalpost_changes(project: Project, base: str) -> list[str]:
    git = GitRepository(project.root)
    changed = git.changed_files(base)
    before_text = git.file_at(base, CONTRACT_FILE)
    changes = []
    if before_text is not None:
        before = parse_contract(tomllib.loads(before_text))
        changes += contract_changes(before, project.contract, project.rules)
    changes += eval_changes(git, base, changed)
    return changes + [
        f"guarded file changed: {path}" for path in changed if path.startswith(GUARDED_FILES)
    ]


def approver_at(project: Project, base: str) -> str:
    """The approver as the base commit names them, so a pull request can't name its own."""
    before_text = GitRepository(project.root).file_at(base, CONTRACT_FILE)
    if before_text is None:
        return project.contract.approver
    return parse_contract(tomllib.loads(before_text)).approver


def goalposts_command(cwd: Path, base: str) -> int:
    project = load_project(cwd)
    changes = goalpost_changes(project, base)
    if not changes:
        say("Goalposts unchanged.")
        return 0
    say("Changes that need Omar's approval:\n" + "\n".join(f"  {change}" for change in changes))
    if owner_approved(os.environ, approver_at(project, base)):
        say("Approved by the owner on this commit.")
        return 0
    complain("Not approved yet: the merge waits for the owner's approval of this commit.")
    return 1


def branch_item(project: Project, git: GitRepository) -> WorkItem | None:
    branch = pull_request_branch(os.environ) or git.current_branch()
    if not branch.startswith("item/"):
        return None
    return project.work_item(branch.removeprefix("item/").split("-", 1)[0])


def size_problems(item: WorkItem, files: int, lines: int, project: Project) -> list[str]:
    """A pull request stays small enough to review: changed lines and files within budget."""
    rules, problems = project.rules, []
    if lines > rules.limit("item_lines"):
        problems.append(
            f"Item {item.id} changes {lines} lines; the budget is "
            f"{rules.limit('item_lines')}: split it."
        )
    if files > rules.limit("item_files"):
        problems.append(
            f"Item {item.id} changes {files} files; the budget is "
            f"{rules.limit('item_files')}: split it."
        )
    return problems


def scope_command(cwd: Path, base: str) -> int:
    project = load_project(cwd)
    git = GitRepository(project.root)
    item = branch_item(project, git)
    if item is None:
        complain("This branch is not a work item (item/<id>-<title>) with a file in work/.")
        return 1
    files = git.changed_files(base)
    problems = [f"{path} is outside item {item.id}'s scope" for path in item.out_of_scope(files)]
    problems += size_problems(item, len(files), git.changed_lines(base), project)
    for problem in problems:
        complain(problem)
    say(f"Item {item.id} ({item.kind}): {len(files)} files, {git.changed_lines(base)} lines.")
    return 1 if problems else 0


def red_first_command(cwd: Path, base: str) -> int:
    project = load_project(cwd)
    git = GitRepository(project.root)
    item = branch_item(project, git)
    if item is None or not item.red_first:
        say("No failing test required for this branch.")
        return 0
    verdict = tests_fail_on_base(project, git, base)
    (say if verdict.ok else complain)(verdict.message)
    return 0 if verdict.ok else 1
