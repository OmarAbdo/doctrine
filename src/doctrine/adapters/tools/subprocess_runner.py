"""Runs the standard tools as subprocesses of the Python doctrine itself runs on."""

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from doctrine.application.ports import ToolResult

MODULES = {
    "ruff": "ruff",
    "ruff-format": "ruff",
    "pylint": "pylint",
    "mypy": "mypy",
    "pytest": "pytest",
    "coverage": "coverage",
    "diff-cover": "diff_cover.diff_cover_tool",
}
TIMEOUT_SECONDS = 900


class SubprocessRunner:
    """Runs tools in `root` with `import_roots` on the import path."""

    def __init__(self, root: Path, import_roots: Sequence[Path]) -> None:
        self.root, self.import_roots = root, import_roots

    def environment(self) -> dict[str, str]:
        paths = [str(path) for path in self.import_roots]
        return {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(paths),
            "MYPYPATH": os.pathsep.join(paths),
            "PYTHONIOENCODING": "utf-8",
        }

    def run(self, name: str, arguments: Sequence[str]) -> ToolResult:
        command = [sys.executable, "-m", MODULES[name], *arguments]
        try:
            finished = subprocess.run(
                command,
                cwd=self.root,
                env=self.environment(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                name=name, passed=False, output=f"{name} ran over {TIMEOUT_SECONDS} s"
            )
        output = (finished.stdout + finished.stderr).strip()
        return ToolResult(
            name=name, passed=finished.returncode == 0, output=output, exit_code=finished.returncode
        )
