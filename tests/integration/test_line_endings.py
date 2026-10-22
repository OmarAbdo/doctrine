"""A change of line endings alone (CRLF to LF) is no change a reviewer reads."""

from pathlib import Path

from support.projects import commit_all, git, write

from doctrine.adapters.cli.gates import ci_commands
from doctrine.adapters.tools.git_repository import GitRepository, line_ending_only

ITEM = 'id = "1"\ntitle = "Line endings"\nkind = "chore"\nscope = ["notes/**"]\n'
FILES = 20


def windows_files(project: Path) -> None:
    git(project, "config", "core.autocrlf", "false")
    # New projects store text with LF; these notes keep the CRLF a repository from before had.
    with (project / ".gitattributes").open("a", encoding="utf-8") as attributes:
        attributes.write("notes/** -text\n")
    for number in range(FILES):
        (project / f"notes/{number}.txt").parent.mkdir(exist_ok=True)
        (project / f"notes/{number}.txt").write_bytes(b"one\r\ntwo\r\nthree\r\n")
    commit_all(project, "Notes written on Windows")


def test_line_endings_alone_count_no_lines_and_no_files(project: Path) -> None:
    windows_files(project)
    git(project, "switch", "-q", "-c", "item/1-line-endings")
    write(project, "work/1-line-endings.toml", ITEM)
    for number in range(FILES):
        (project / f"notes/{number}.txt").write_bytes(b"one\ntwo\nthree\n")
    (project / "notes/0.txt").write_bytes(b"one\ntwo\nthree\nfour\n")
    commit_all(project, "Unix line endings")
    repository = GitRepository(project)
    assert repository.changed_lines("main") == 5
    assert len(line_ending_only(repository, "main")) == FILES - 1
    assert ci_commands.scope_command(project, "main") == 0
