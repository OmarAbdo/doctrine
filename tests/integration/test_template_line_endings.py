"""A new project stores text with LF from its first commit, like doctrine itself (#37)."""

from pathlib import Path

from support.projects import git


def test_a_new_project_stores_text_with_lf(project: Path) -> None:
    attributes = (project / ".gitattributes").read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in attributes
    endings = git(project, "ls-files", "--eol", "doctrine.toml", "CLAUDE.md")
    assert endings.count("i/lf") == 2
