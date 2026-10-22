"""New projects pin a release tag, so a new version on main must get its tag without anyone
remembering to push it (read as text: no YAML parser among the pinned tools)."""

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"


def test_main_tags_a_version_that_has_no_tag_yet() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    triggers = text.split("\non:", 1)[1].split("\npermissions:", 1)[0]
    assert "push:" in triggers
    assert "branches: [main]" in triggers
    assert "contents: write" in text
    assert "pyproject.toml" in text
    assert 'git tag "v$version"' in text
    assert "refs/tags/v$version" in text
