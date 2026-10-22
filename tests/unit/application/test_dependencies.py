from collections.abc import Sequence

from doctrine.application.dependencies import lock_dependencies
from doctrine.domain.dependencies.locking import Pin


class FixedResolver:
    def __init__(self) -> None:
        self.asked: list[Sequence[str]] = []

    def resolve(self, requirements: Sequence[str]) -> list[Pin]:
        self.asked.append(requirements)
        return [Pin("httpx", "0.28.1")]


class FixedIndex:
    def hashes(self, pin: Pin) -> list[str]:
        return [f"{pin.name}-hash"]


def test_declared_dependencies_are_resolved_and_hashed() -> None:
    resolver = FixedResolver()
    text = lock_dependencies(["httpx"], resolver, FixedIndex())
    assert resolver.asked == [["httpx"]]
    assert "httpx==0.28.1 \\\n    --hash=sha256:httpx-hash" in text


def test_no_dependencies_need_no_resolution() -> None:
    resolver = FixedResolver()
    text = lock_dependencies([], resolver, FixedIndex())
    assert resolver.asked == []
    assert [line for line in text.splitlines() if not line.startswith("#")] == []
