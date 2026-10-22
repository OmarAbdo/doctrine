"""An AI task's command, run once per eval case: the case's input as JSON on its standard input,
its answer on its standard output. A crash or a timeout is no answer."""

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from doctrine.domain.evals.cases import EvalCase

TIMEOUT_SECONDS = 300


class TaskCommand:
    def __init__(
        self, root: Path, command: Sequence[str], environment: Mapping[str, str] | None = None
    ) -> None:
        self.root, self.command, self.environment = root, list(command), environment

    def answer(self, case: EvalCase) -> str | None:
        try:
            finished = subprocess.run(
                self.command,
                cwd=self.root,
                env=self.environment,
                input=json.dumps(case.input),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return finished.stdout.strip() if finished.returncode == 0 else None
