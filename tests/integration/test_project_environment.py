"""A project's own environment (#45, #47): its locked dependencies importable by its tests and
commands, built from local wheels here so the test needs no network."""

import hashlib
import subprocess
import zipfile
from pathlib import Path

from support.projects import write

from doctrine.adapters.cli.commands.item_commands import metric_record
from doctrine.adapters.storage.metric_log import latest_metric
from doctrine.adapters.storage.project_files import Project
from doctrine.adapters.tools.project_environment import ProjectEnvironment, project_command

OUTCOME = "def main() -> None:\n    print(3)\n\n\nmain()\n"


def wheel(folder: Path, name: str) -> str:
    """A wheel holding one importable module; returns its sha256 for a lock line."""
    path = folder / f"{name}-1.0-py3-none-any.whl"
    info = f"{name}-1.0.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}/__init__.py", "ANSWER = 42\n")
        archive.writestr(f"{info}/METADATA", f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n")
        archive.writestr(
            f"{info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )
        archive.writestr(f"{info}/RECORD", "")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locked_project(project: Path, wheels: Path) -> ProjectEnvironment:
    tool_hash, dependency_hash = wheel(wheels, "sometool"), wheel(wheels, "somelib")
    tools = write(wheels, "tools.txt", f"sometool==1.0 --hash=sha256:{tool_hash}\n")
    write(project, "requirements.lock", f"somelib==1.0 --hash=sha256:{dependency_hash}\n")
    options = ["--no-index", "--find-links", str(wheels)]
    return ProjectEnvironment(Project.load(project), tools=tools, pip_options=options)


def imports(python: str, module: str) -> bool:
    finished = subprocess.run([python, "-c", f"import {module}"], check=False, timeout=60)
    return finished.returncode == 0


def test_the_environment_holds_the_tools_and_the_locked_dependencies(
    project: Path, tmp_path: Path
) -> None:
    environment = locked_project(project, tmp_path)
    python = environment.python()
    assert Path(python).is_relative_to(project / ".venv")
    assert imports(python, "somelib") and imports(python, "sometool")
    stamp = project / ".venv" / "doctrine-environment.txt"
    built = stamp.stat().st_mtime_ns
    assert environment.python() == python
    assert stamp.stat().st_mtime_ns == built


def test_without_a_lock_the_project_runs_on_doctrines_python(project: Path) -> None:
    assert not ProjectEnvironment(Project.load(project)).python().startswith(str(project))


def test_python_in_a_command_is_the_projects_and_its_package_imports(project: Path) -> None:
    command, environment = project_command(Project.load(project), ("python", "-m", "x"))
    assert command[0] != "python"
    assert str(project / "src") in environment["PYTHONPATH"]


def test_the_outcome_command_imports_the_project_package(project: Path) -> None:
    """#47: `python -m <package>.adapters.outcome` found no package under src/."""
    write(project, "src/sample_jobs/adapters/outcome.py", OUTCOME)
    assert metric_record(project) == 0
    assert latest_metric(project) == 3
