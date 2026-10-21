from pathlib import Path

import pytest
from support.projects import git, write

from doctrine.adapters.cli import check_commands, item_commands
from doctrine.adapters.cli.console import NoProjectError, load_project
from doctrine.adapters.cli.init_command import init_command
from doctrine.adapters.cli.main import main
from doctrine.adapters.storage.metric_log import latest_metric
from doctrine.adapters.storage.state_store import StateStore
from doctrine.adapters.tools.git_repository import GitRepository

FAILING_TEST = (
    "from sample_jobs.domain.title import tidy_title\n\n\n"
    "def test_titles_lose_their_gender_suffix() -> None:\n"
    '    assert tidy_title("Engineer (m/w/d)") == "Engineer"\n'
)
TITLE_MODULE = 'def tidy_title(title: str) -> str:\n    return title.removesuffix(" (m/w/d)")\n'


def test_outside_a_project_commands_say_how_to_start_one(tmp_path: Path) -> None:
    with pytest.raises(NoProjectError, match="doctrine init"):
        load_project(tmp_path)


def test_init_refuses_a_folder_that_is_already_a_project(project: Path) -> None:
    assert init_command(project, "Again", "OmarAbdo") == 1


def test_a_feature_goes_red_then_green_then_passes_the_check(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project)
    scope = "src/sample_jobs/domain/**"
    assert (
        main(["item", "start", "--kind", "feature", "--title", "Tidy titles", "--scope", scope])
        == 0
    )
    assert GitRepository(project).current_branch() == "item/1-tidy-titles"
    assert item_commands.item_start(project, "fix", "Another", [scope]) == 1
    write(project, "tests/unit/test_title.py", FAILING_TEST)
    assert check_commands.test_command(project, []) == 1
    assert main(["item", "done"]) == 1
    write(project, "src/sample_jobs/domain/title.py", TITLE_MODULE)
    assert check_commands.test_command(project, []) == 0
    assert main(["check"]) == 0
    assert main(["item", "done"]) == 0
    assert StateStore(project).active_item() is None


def test_the_outcome_metric_is_recorded_from_its_command(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = project / "doctrine.toml"
    old_command = 'command = ["python", "-m", "sample_jobs.adapters.outcome"]'
    text = contract.read_text(encoding="utf-8").replace(
        old_command, 'command = ["python", "-c", "print(3)"]'
    )
    contract.write_text(text, encoding="utf-8")
    monkeypatch.chdir(project)
    assert main(["metric", "record"]) == 0
    assert latest_metric(project) == 3.0


def test_item_numbers_count_the_items_on_other_branches(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(project, "branch", "item/4-started-elsewhere")
    monkeypatch.chdir(project)
    scope = "src/sample_jobs/domain/**"
    assert main(["item", "start", "--kind", "chore", "--title", "Next", "--scope", scope]) == 0
    assert GitRepository(project).current_branch() == "item/5-next"
