"""Resolves requirements with pip itself (`pip install --dry-run --report`); nothing installed."""

import json
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from doctrine.domain.dependencies.locking import Pin, resolved_pins

TIMEOUT_SECONDS = 600


class PipResolver:
    def __init__(self, options: Sequence[str] = ()) -> None:
        self.options = list(options)

    def resolve(self, requirements: Sequence[str]) -> list[Pin]:
        with tempfile.TemporaryDirectory(prefix="doctrine-resolve-") as folder:
            report = Path(folder) / "report.json"
            command = [sys.executable, "-m", "pip", "install", "--dry-run", "--ignore-installed"]
            command += ["--quiet", "--report", str(report), *self.options, *requirements]
            finished = subprocess.run(
                command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
            )
            if finished.returncode != 0:
                raise RuntimeError(f"pip couldn't resolve {list(requirements)}:\n{finished.stderr}")
            return resolved_pins(json.loads(report.read_text(encoding="utf-8")))
