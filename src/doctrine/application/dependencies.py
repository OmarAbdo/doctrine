"""Locking a project's declared dependencies: resolve them, then hash every published file."""

from collections.abc import Sequence
from typing import Protocol

from doctrine.domain.dependencies.locking import Pin, lock_text


class Resolver(Protocol):
    def resolve(self, requirements: Sequence[str]) -> list[Pin]: ...


class Index(Protocol):
    def hashes(self, pin: Pin) -> list[str]: ...


def lock_dependencies(requirements: Sequence[str], resolver: Resolver, index: Index) -> str:
    pins = resolver.resolve(requirements) if requirements else []
    return lock_text({pin: index.hashes(pin) for pin in pins})
