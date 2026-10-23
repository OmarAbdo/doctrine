"""#59: the file tools were refused on work/ and metrics/, the shell wasn't. A made-up metric value
or a widened item scope went around the guard."""

import pytest

from doctrine.domain.safety.command_policy import CommandContext, judge_command

ON_ITEM = CommandContext(current_branch="item/3-fit", in_project=True)


@pytest.mark.parametrize(
    "command",
    [
        """echo '{"value": 99}' >> metrics/outcome.jsonl""",
        """echo 'scope = ["src/**"]' >> work/3-fit.toml""",
        "cp other.toml work/3-fit.toml",
        "sed -i 's/doctrine.toml/src/' work/3-fit.toml",
    ],
)
def test_shell_writes_to_command_owned_files_are_refused(command: str) -> None:
    verdict = judge_command(command, ON_ITEM)
    assert verdict.rule == "command-owned"
    assert "doctrine item scope" in verdict.reason


@pytest.mark.parametrize(
    "command",
    [
        "git add work/3-fit.toml metrics/outcome.jsonl",
        "cat work/3-fit.toml",
        "doctrine metric record",
        "doctrine item scope src/fit/**",
    ],
)
def test_reading_committing_and_doctrines_own_commands_are_fine(command: str) -> None:
    assert judge_command(command, ON_ITEM).allowed


def test_outside_a_project_a_work_folder_is_anyones() -> None:
    outside = CommandContext(current_branch="main", in_project=False)
    assert judge_command("echo notes > work/3-plan.toml", outside).allowed


def test_a_separator_inside_quotes_does_not_split_the_command() -> None:
    """The self-test found it: `|` inside a quoted sed expression cut the command in pieces, so
    no piece held both the write and the path."""
    verdict = judge_command("sed -i 's|domain|everything|' work/3-fit.toml", ON_ITEM)
    assert verdict.rule == "command-owned"
    assert judge_command("echo 'a; b' && git status", ON_ITEM).allowed
