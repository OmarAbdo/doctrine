import pytest

from doctrine.domain.safety.protected import is_protected, mentions_protected


@pytest.mark.parametrize(
    "path",
    [
        r"D:\work\jobs\.doctrine\state.json",
        "C:/Program Files/Doctrine/rules/rules.toml",
        r"C:\Program Files\ClaudeCode\managed-settings.json",
        "D:/work/jobs/.git/hooks/pre-commit",
        "D:/work/jobs/.github/workflows/doctrine.yml",
        "D:/work/jobs/.github/CODEOWNERS",
        "C:/Users/Omar/.claude/settings.json",
    ],
)
def test_doctrine_and_claude_code_settings_files_are_protected(path: str) -> None:
    assert is_protected(path)


@pytest.mark.parametrize(
    "path",
    [
        "D:/work/jobs/src/jobs/domain/job.py",
        "D:/work/jobs/doctrine.toml",
        "D:/work/jobs/.github/workflows/release.yml",
    ],
)
def test_project_files_are_not_protected(path: str) -> None:
    assert not is_protected(path)


def test_a_command_mentioning_a_protected_path_is_recognised() -> None:
    assert mentions_protected(r"cat C:\Program Files\Doctrine\rules\rules.toml")
