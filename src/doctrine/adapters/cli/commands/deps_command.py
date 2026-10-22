"""`doctrine deps lock`: the dependencies in pyproject.toml, resolved and hashed into
requirements.lock, which the project's environment is built from."""

import tomllib
from pathlib import Path

from doctrine.adapters.cli.console import complain, load_project, say
from doctrine.adapters.tools.package_index import PackageIndex
from doctrine.adapters.tools.pip_resolver import PipResolver
from doctrine.application.dependencies import lock_dependencies
from doctrine.domain.dependencies.locking import LOCK_FILE, declared


def deps_lock(cwd: Path) -> int:
    project = load_project(cwd)
    pyproject = project.root / "pyproject.toml"
    if not pyproject.is_file():
        complain(f"There is no pyproject.toml in {project.root} to read dependencies from.")
        return 1
    requirements = declared(tomllib.loads(pyproject.read_text(encoding="utf-8")))
    text = lock_dependencies(requirements, PipResolver(), PackageIndex())
    (project.root / LOCK_FILE).write_text(text, encoding="utf-8", newline="\n")
    pins = sum(1 for line in text.splitlines() if "==" in line)
    say(f"{LOCK_FILE}: {pins} packages locked for {len(requirements)} declared dependencies.")
    return 0
