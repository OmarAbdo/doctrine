from dataclasses import replace

import pytest

from doctrine.application.guard import Situation, ToolEvent, decide_stop, decide_tool_use
from doctrine.domain.governance.work_item import WorkItem

ITEM = WorkItem(id="7", title="Search by city", kind="feature", scope=("src/jobs/search/**",))
READY = Situation(
    root="D:/work/jobs",
    source_roots=("src/jobs",),
    branch="item/7-search-by-city",
    item=ITEM,
    red_seen=True,
    line_stopped=False,
    unchecked_changes=False,
)


def edit(path: str) -> ToolEvent:
    return ToolEvent(tool="Edit", tool_input={"file_path": path})


def shell(command: str) -> ToolEvent:
    return ToolEvent(tool="Bash", tool_input={"command": command})


def test_an_edit_inside_the_item_scope_is_allowed() -> None:
    assert decide_tool_use(edit("D:/work/jobs/src/jobs/search/query.py"), READY).allowed


def test_an_edit_outside_the_item_scope_is_refused() -> None:
    decision = decide_tool_use(edit("D:/work/jobs/src/jobs/mail/send.py"), READY)
    assert not decision.allowed
    assert "outside item 7" in decision.reason


def test_an_edit_without_an_active_item_is_refused() -> None:
    decision = decide_tool_use(
        edit("D:/work/jobs/src/jobs/search/query.py"), replace(READY, item=None)
    )
    assert not decision.allowed
    assert "doctrine item start" in decision.reason


def test_production_code_waits_for_a_failing_test_on_a_feature() -> None:
    waiting = replace(READY, red_seen=False)
    assert not decide_tool_use(edit("D:/work/jobs/src/jobs/search/query.py"), waiting).allowed
    assert decide_tool_use(edit("D:/work/jobs/tests/unit/test_query.py"), waiting).allowed


def test_a_refactor_needs_no_failing_test() -> None:
    refactor = replace(READY, red_seen=False, item=replace(ITEM, kind="refactor"))
    assert decide_tool_use(edit("D:/work/jobs/src/jobs/search/query.py"), refactor).allowed


def test_while_the_line_is_stopped_only_a_restore_item_may_change_code() -> None:
    stopped = replace(READY, line_stopped=True)
    decision = decide_tool_use(edit("D:/work/jobs/src/jobs/search/query.py"), stopped)
    assert not decision.allowed
    assert "line is stopped" in decision.reason
    restoring = replace(stopped, item=replace(ITEM, kind="restore"))
    assert decide_tool_use(edit("D:/work/jobs/src/jobs/search/query.py"), restoring).allowed


@pytest.mark.parametrize(
    "path",
    [
        "D:/work/jobs/.doctrine/state.json",
        "C:/Program Files/Doctrine/rules/rules.toml",
        "D:/work/jobs/.github/workflows/doctrine.yml",
    ],
)
def test_doctrine_files_are_never_edited_by_hand(path: str) -> None:
    assert not decide_tool_use(edit(path), READY).allowed


def test_files_outside_any_project_are_free_but_still_not_doctrine_files() -> None:
    nowhere = replace(READY, root=None)
    assert decide_tool_use(edit("C:/Users/Omar/notes.md"), nowhere).allowed
    assert not decide_tool_use(edit("C:/Program Files/Doctrine/x.py"), nowhere).allowed


def test_shell_commands_go_through_the_command_policy() -> None:
    assert not decide_tool_use(shell("git commit --no-verify -m x"), READY).allowed
    assert decide_tool_use(shell("git status"), READY).allowed


def test_powershell_commands_are_judged_the_same_way() -> None:
    event = ToolEvent(tool="PowerShell", tool_input={"command": "git push origin main"})
    assert not decide_tool_use(event, READY).allowed


def test_a_success_claim_over_unchecked_changes_cannot_end_the_turn() -> None:
    unchecked = replace(READY, unchecked_changes=True)
    decision = decide_stop("Search by city is fixed and works.", unchecked)
    assert not decision.allowed
    assert "doctrine check" in decision.reason


def test_an_honest_report_over_unchecked_changes_may_end_the_turn() -> None:
    unchecked = replace(READY, unchecked_changes=True)
    assert decide_stop("I changed the query; it isn't checked yet.", unchecked).allowed


def test_a_claim_after_a_passing_check_may_end_the_turn() -> None:
    assert decide_stop("Search by city works; doctrine check passed.", READY).allowed


def test_outside_a_project_pushing_main_is_allowed() -> None:
    nowhere = replace(READY, root=None, branch="main")
    assert decide_tool_use(shell("git push origin main"), nowhere).allowed


@pytest.mark.parametrize(
    "path",
    [
        "D:/work/jobs/work/7-search-by-city.toml",
        "D:/work/jobs/metrics/outcome.jsonl",
    ],
)
def test_work_items_and_the_metric_history_are_written_by_doctrine_commands_only(path: str) -> None:
    decision = decide_tool_use(edit(path), READY)
    assert not decision.allowed
    assert "doctrine" in decision.reason
