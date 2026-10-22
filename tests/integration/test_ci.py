import json
from pathlib import Path

import pytest
from support.projects import commit_all, git, write

from doctrine.adapters.cli import ci_commands, github_reviews, red_first
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.git_repository import GitRepository

ITEM = 'id = "1"\ntitle = "Tidy titles"\nkind = "feature"\nscope = ["src/sample_jobs/domain/**"]\n'


def item_branch(project: Path) -> None:
    git(project, "switch", "-q", "-c", "item/1-tidy-titles")
    write(project, "work/1-tidy-titles.toml", ITEM)


def set_limits(project: Path, limits: str) -> None:
    contract = project / "doctrine.toml"
    contract.write_text(
        contract.read_text(encoding="utf-8") + f"\n[limits]\n{limits}\n", encoding="utf-8"
    )


def test_tightening_passes_and_loosening_waits_for_the_approver(project: Path) -> None:
    set_limits(project, "function_lines = 30")
    commit_all(project, "Tighter functions")
    git(project, "switch", "-q", "-c", "item/2-looser")
    contract = project / "doctrine.toml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("= 30", "= 25"), encoding="utf-8"
    )
    commit_all(project, "Even tighter")
    assert ci_commands.goalposts_command(project, "main") == 0
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("= 25", "= 35"), encoding="utf-8"
    )
    commit_all(project, "Looser")
    changes = ci_commands.goalpost_changes(Project.load(project), "main")
    assert changes == ["limit function_lines: 30 -> 35"]
    assert ci_commands.goalposts_command(project, "main") == 1


def test_an_approval_counts_only_from_the_approver_on_the_current_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 7, "head": {"sha": "abc"}}}))
    environment = {"GITHUB_EVENT_PATH": str(event), "GITHUB_REPOSITORY": "OmarAbdo/jobs"}
    approvals = [
        {"state": "APPROVED", "user": {"login": "OmarAbdosBot"}, "commit_id": "abc"},
        {"state": "APPROVED", "user": {"login": "OmarAbdo"}, "commit_id": "old"},
    ]
    monkeypatch.setattr(github_reviews, "reviews", lambda repository, number: approvals)
    assert not github_reviews.owner_approved(environment, "OmarAbdo")
    approvals.append({"state": "APPROVED", "user": {"login": "omarabdo"}, "commit_id": "abc"})
    assert github_reviews.owner_approved(environment, "OmarAbdo")


def test_a_file_outside_the_item_scope_fails_the_scope_gate(project: Path) -> None:
    item_branch(project)
    write(project, "src/sample_jobs/domain/title.py", "SUFFIX = ' (m/w/d)'\n")
    commit_all(project, "Inside the scope")
    assert ci_commands.scope_command(project, "main") == 0
    write(project, "src/sample_jobs/adapters/mail.py", "SENDER = 'jobs'\n")
    commit_all(project, "Outside the scope")
    assert ci_commands.scope_command(project, "main") == 1


def test_a_new_test_must_fail_on_the_code_before_the_item(project: Path) -> None:
    item_branch(project)
    write(
        project,
        "tests/unit/test_title.py",
        "from sample_jobs.domain.title import SUFFIX\n\n\ndef test_suffix() -> None:\n"
        "    assert SUFFIX == ' (m/w/d)'\n",
    )
    write(project, "src/sample_jobs/domain/title.py", "SUFFIX = ' (m/w/d)'\n")
    commit_all(project, "Suffix with its test")
    verdict = red_first.tests_fail_on_base(Project.load(project), GitRepository(project), "main")
    assert verdict.ok, verdict.message
    assert ci_commands.red_first_command(project, "main") == 0


def test_a_test_that_passes_without_the_change_proves_nothing(project: Path) -> None:
    item_branch(project)
    write(
        project, "tests/unit/test_arithmetic.py", "def test_sum() -> None:\n    assert 1 + 1 == 2\n"
    )
    commit_all(project, "A test that proves nothing")
    verdict = red_first.tests_fail_on_base(Project.load(project), GitRepository(project), "main")
    assert not verdict.ok
    assert "prove nothing" in verdict.message


def test_an_approval_run_finds_the_item_from_the_pull_request_event(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item_branch(project)
    write(project, "src/sample_jobs/domain/title.py", "SUFFIX = ' (m/w/d)'\n")
    commit_all(project, "Inside the scope")
    git(project, "switch", "-q", "--detach")
    event = tmp_path / "review.json"
    head = {"ref": "item/1-tidy-titles", "sha": "abc"}
    event.write_text(
        json.dumps({"pull_request": {"number": 7, "head": head, "base": {"ref": "main"}}})
    )
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert ci_commands.scope_command(project, "main") == 0


def test_a_changed_eval_label_needs_the_approver(project: Path) -> None:
    write(project, "evals/titles/cases.jsonl", '{"id": "a", "label": "good"}\n')
    commit_all(project, "First eval case")
    item_branch(project)
    write(
        project,
        "evals/titles/cases.jsonl",
        '{"id": "a", "label": "bad"}\n{"id": "b", "label": "good"}\n',
    )
    commit_all(project, "Relabel")
    changes = ci_commands.goalpost_changes(Project.load(project), "main")
    assert changes == ["evals/titles/cases.jsonl: eval case a: label good -> bad"]


def test_an_approved_change_passes_the_goalposts(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item_branch(project)
    write(project, ".github/workflows/extra.yml", "name: extra\n")
    commit_all(project, "A guarded file")
    monkeypatch.setattr(ci_commands, "owner_approved", lambda environment, approver: True)
    assert ci_commands.goalposts_command(project, "main") == 0


def test_the_gates_refuse_a_branch_that_is_no_item_and_an_item_over_budget(project: Path) -> None:
    assert ci_commands.scope_command(project, "main") == 1
    item_branch(project)
    write(
        project,
        "src/sample_jobs/domain/big.py",
        "".join(f"VALUE_{number} = {number}\n" for number in range(401)),
    )
    commit_all(project, "Too big")
    assert ci_commands.scope_command(project, "main") == 1


def test_a_rewrite_counts_every_changed_line_not_the_net(project: Path) -> None:
    """Replacing 300 lines with 300 others adds 0 lines net but changes 600 for a reviewer."""
    lines = "".join(f"OLD_{number} = {number}\n" for number in range(300))
    write(project, "src/sample_jobs/domain/table.py", lines)
    commit_all(project, "A table")
    item_branch(project)
    write(project, "src/sample_jobs/domain/table.py", lines.replace("OLD_", "NEW_"))
    commit_all(project, "The table rewritten")
    assert ci_commands.scope_command(project, "main") == 1


def test_an_item_touching_too_many_files_is_split(project: Path) -> None:
    item_branch(project)
    for number in range(16):
        write(project, f"src/sample_jobs/domain/part_{number}.py", f"PART = {number}\n")
    commit_all(project, "Sixteen files")
    assert ci_commands.scope_command(project, "main") == 1


def test_a_chore_needs_no_failing_test(project: Path) -> None:
    git(project, "switch", "-q", "-c", "item/2-tidy-readme")
    write(
        project,
        "work/2-tidy-readme.toml",
        'id = "2"\ntitle = "Tidy readme"\nkind = "chore"\nscope = ["README.md"]\n',
    )
    commit_all(project, "Chore")
    assert ci_commands.red_first_command(project, "main") == 0
