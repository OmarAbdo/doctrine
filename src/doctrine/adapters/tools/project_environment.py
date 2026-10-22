"""A project's own Python environment (.venv): doctrine's pinned tools plus the project's locked
dependencies (requirements.lock), so its tests, type checks and commands import what it imports.
It is rebuilt whenever either lock or the Python changes. A project without a lock runs on
doctrine's own Python, as before."""

import hashlib
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from doctrine.adapters.storage.project_files import DOCTRINE_HOME, Project
from doctrine.domain.dependencies.locking import LOCK_FILE

FOLDER = ".venv"
STAMP = "doctrine-environment.txt"
TOOLS = DOCTRINE_HOME / "requirements" / "tools.txt"
BUILD_TIMEOUT_SECONDS = 1200
PYTHON_NAMES = frozenset({"python", "python3"})


class ProjectEnvironment:
    def __init__(
        self, project: Project, tools: Path = TOOLS, pip_options: Sequence[str] = ()
    ) -> None:
        self.project, self.tools, self.pip_options = project, tools, list(pip_options)
        self.folder = project.root / FOLDER

    def python(self) -> str:
        lock = self.project.root / LOCK_FILE
        if not lock.is_file():
            return sys.executable
        wanted = fingerprint(self.tools, lock)
        stamp = self.folder / STAMP
        if not stamp.is_file() or stamp.read_text(encoding="utf-8") != wanted:
            self.build(lock)
            stamp.write_text(wanted, encoding="utf-8")
        return str(interpreter(self.folder))

    def build(self, lock: Path) -> None:
        shutil.rmtree(self.folder, ignore_errors=True)
        run([getattr(sys, "_base_executable", sys.executable), "-m", "venv", str(self.folder)])
        install = ["-m", "pip", "install", "--quiet", "--require-hashes", *self.pip_options]
        run([str(interpreter(self.folder)), *install, "-r", str(self.tools), "-r", str(lock)])


def interpreter(folder: Path) -> Path:
    if os.name == "nt":
        return folder / "Scripts" / "python.exe"
    return folder / "bin" / "python"


def fingerprint(tools: Path, lock: Path) -> str:
    content = tools.read_bytes() + lock.read_bytes() + sys.version.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def run(command: list[str]) -> None:
    finished = subprocess.run(
        command, capture_output=True, text=True, timeout=BUILD_TIMEOUT_SECONDS, check=False
    )
    if finished.returncode != 0:
        raise RuntimeError(f"Building the project's environment failed:\n{finished.stderr[-2000:]}")


def import_roots(project: Project, root: Path | None = None) -> list[Path]:
    """The project root and each service's parent folder (`src/`), so its packages import."""
    base = root or project.root
    return [base, *(base / Path(service.path).parent for service in project.contract.services)]


def project_command(project: Project, command: Sequence[str]) -> tuple[list[str], dict[str, str]]:
    """An outcome or AI task command: `python` means the project's, and its packages import."""
    argv = list(command)
    if argv and argv[0] in PYTHON_NAMES:
        argv[0] = ProjectEnvironment(project).python()
    paths = os.pathsep.join(str(path) for path in import_roots(project))
    return argv, {**os.environ, "PYTHONPATH": paths, "PYTHONIOENCODING": "utf-8"}
