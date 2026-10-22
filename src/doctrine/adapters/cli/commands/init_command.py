"""`doctrine init`: a new project from the template, with its git hook installed."""

import re
import subprocess
from pathlib import Path

from doctrine import __version__
from doctrine.adapters.cli.console import complain, say
from doctrine.adapters.storage.project_files import CONTRACT_FILE, DOCTRINE_HOME
from doctrine.adapters.tools.git_repository import NO_DAEMON

TEMPLATE = DOCTRINE_HOME / "templates" / "python-hexagonal"
DOCTRINE_REPOSITORY = "OmarAbdo/doctrine"
PRE_COMMIT = (
    "#!/bin/sh\n"
    "# Installed by doctrine init: every commit passes doctrine check first.\n"
    "exec doctrine check\n"
)
GIT_TIMEOUT_SECONDS = 60


def placeholders(name: str, approver: str) -> dict[str, str]:
    return {
        "name": name,
        "package": re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"),
        "approver": approver,
        "version": __version__,
        "doctrine_repository": DOCTRINE_REPOSITORY,
    }


def fill(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def copy_template(target: Path, values: dict[str, str]) -> list[Path]:
    written = []
    for source in sorted(path for path in TEMPLATE.rglob("*") if path.is_file()):
        destination = target / fill(source.relative_to(TEMPLATE).as_posix(), values)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(fill(source.read_text(encoding="utf-8"), values), encoding="utf-8")
        written.append(destination)
    return written


def install_git_hook(target: Path) -> None:
    if not (target / ".git").exists():
        subprocess.run(
            ["git", *NO_DAEMON, "init", "-q", "-b", "main"],
            cwd=target,
            check=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    hook = target / ".git" / "hooks" / "pre-commit"
    hook.write_text(PRE_COMMIT, encoding="utf-8", newline="\n")
    hook.chmod(0o755)


def init_command(cwd: Path, name: str, approver: str) -> int:
    if (cwd / CONTRACT_FILE).exists():
        complain(f"{cwd} is already a doctrine project.")
        return 1
    written = copy_template(cwd, placeholders(name, approver))
    install_git_hook(cwd)
    say(
        f"Doctrine project {name}: {len(written)} files, pre-commit hook installed.\n"
        "First item: agree the outcome metric with the approver and define it in doctrine.toml."
    )
    return 0
