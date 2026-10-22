"""What the application needs from the outside world, as small interfaces the adapters implement."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolResult:
    name: str
    passed: bool
    output: str


class ToolRunner(Protocol):
    def run(self, name: str, arguments: Sequence[str]) -> ToolResult: ...
