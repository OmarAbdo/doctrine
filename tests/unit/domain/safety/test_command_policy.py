import pytest

from doctrine.domain.safety.command_policy import CommandContext, judge_command

ON_ITEM = CommandContext(current_branch="item/7-search", in_project=True)
ON_MAIN = CommandContext(current_branch="main", in_project=True)
OUTSIDE = CommandContext(current_branch="main", in_project=False)

REFUSED = [
    ("git commit --no-verify -m 'x'", "skip-hooks"),
    ("git commit -nm 'x'", "skip-hooks"),
    ("SKIP=ruff git commit -m x", "skip-hooks"),
    ("git -c core.hooksPath=/dev/null commit -m x", "hooks-path"),
    ("git config core.hooksPath .nohooks", "hooks-path"),
    ("git push --force origin item/7-search", "force-push"),
    ("git push -f", "force-push"),
    ("git push origin +item/7-search", "force-push"),
    ("git push origin main", "push-main"),
    ("git push origin HEAD:master", "push-main"),
    ("git push origin HEAD:refs/heads/main", "push-main"),
    ("gh pr merge 12 --squash", "github-admin"),
    ("gh api -X PUT repos/o/r/branches/main/protection", "github-admin"),
    ("gh repo edit --visibility public", "github-admin"),
    ("gh auth token", "credentials"),
    ("git credential fill", "credentials"),
    ("cmdkey /list", "credentials"),
    ("Start-Process powershell -Verb RunAs", "elevation"),
    ("sudo rm -rf /", "elevation"),
    ("echo x > .doctrine/evidence.jsonl", "protected-path"),
    ("sed -i 's/40/90/' 'C:/Program Files/Doctrine/rules/rules.toml'", "protected-path"),
    ("Remove-Item .git/hooks/pre-commit", "protected-path"),
    ("cp evil.yml .github/workflows/doctrine.yml", "protected-path"),
    ("DOCTRINE_OFF=1 python -m doctrine check", "doctrine-override"),
]


@pytest.mark.parametrize(("command", "rule"), REFUSED)
def test_a_way_around_the_gates_is_refused(command: str, rule: str) -> None:
    verdict = judge_command(command, ON_ITEM)
    assert verdict.allowed is False
    assert verdict.rule == rule


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'Add search'",
        "git push -u origin item/7-search",
        "git push -u origin item/8-main-menu",
        "git push --force-with-lease origin item/7-search",
        "gh pr create --fill",
        "gh pr view 12",
        "cat .doctrine/evidence.jsonl",
        "python -m pytest tests/unit",
        "git log --oneline -5",
    ],
)
def test_ordinary_work_is_allowed(command: str) -> None:
    assert judge_command(command, ON_ITEM).allowed is True


def test_committing_or_pushing_on_main_is_refused() -> None:
    assert judge_command("git commit -m 'quick fix'", ON_MAIN).rule == "main-branch"
    assert judge_command("git push", ON_MAIN).rule == "main-branch"
    assert judge_command("git push origin HEAD", ON_MAIN).rule == "main-branch"


@pytest.mark.parametrize(
    "command",
    [
        "git push origin refs/tags/v0.1.0",
        "git push origin --tags",
        "git pull && git push origin refs/tags/v1.2.3",
    ],
)
def test_pushing_only_tags_from_main_is_allowed(command: str) -> None:
    assert judge_command(command, ON_MAIN).allowed


def test_each_command_in_a_line_is_judged_on_its_own() -> None:
    line = "git push -u origin item/5-tags 2>&1 | tail -1; gh pr create --fill --base main"
    assert judge_command(line, ON_ITEM).allowed
    assert not judge_command("git status && git push origin main", ON_ITEM).allowed


def test_a_refusal_says_why_and_what_to_do_instead() -> None:
    verdict = judge_command("git commit --no-verify -m x", ON_ITEM)
    assert "hooks" in verdict.reason
    assert "fix" in verdict.reason


def test_outside_a_project_main_is_open_but_the_other_rules_still_hold() -> None:
    assert judge_command("git commit -m 'update notes'", OUTSIDE).allowed
    assert judge_command("git push origin main", OUTSIDE).allowed
    assert judge_command("git commit --no-verify -m x", OUTSIDE).rule == "skip-hooks"
    assert judge_command("gh auth token", OUTSIDE).rule == "credentials"
