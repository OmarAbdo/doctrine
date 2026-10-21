"""The universal rule table: limits, bans and naming rules every language profile enforces."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal

Bound = Literal["max", "min"]


class LooseningError(ValueError):
    """A project tried to loosen a rule by itself; only an approved change may do that."""


@dataclass(frozen=True)
class Limit:
    name: str
    bound: Bound
    value: int

    def is_looser_than(self, other: "Limit") -> bool:
        if self.bound == "max":
            return self.value > other.value
        return self.value < other.value

    def with_value(self, value: int) -> "Limit":
        return replace(self, value=value)


@dataclass(frozen=True)
class RuleTable:
    limits: Mapping[str, Limit]
    bans: frozenset[str]
    allowed_short: frozenset[str]
    banned_words: frozenset[str]

    def limit(self, name: str) -> int:
        return self.limits[name].value


def parse_limit(name: str, spec: Mapping[str, int]) -> Limit:
    bounds = [bound for bound in ("max", "min") if bound in spec]
    if len(bounds) != 1:
        raise ValueError(f"limit {name} needs exactly one of max or min")
    bound: Bound = "max" if bounds[0] == "max" else "min"
    return Limit(name, bound, int(spec[bound]))


def parse_rule_table(data: Mapping[str, Any]) -> RuleTable:
    names = data.get("names", {})
    return RuleTable(
        limits={name: parse_limit(name, spec) for name, spec in data.get("limits", {}).items()},
        bans=frozenset(ban for ban, active in data.get("bans", {}).items() if active),
        allowed_short=frozenset(names.get("allowed_short", [])),
        banned_words=frozenset(names.get("banned_words", [])),
    )


def tighten(table: RuleTable, overrides: Mapping[str, int]) -> RuleTable:
    """The table with a project's own limits applied; every one must be at least as strict."""
    limits = dict(table.limits)
    for name, value in overrides.items():
        if name not in limits:
            raise ValueError(f"unknown limit {name}")
        wanted = limits[name].with_value(value)
        if wanted.is_looser_than(limits[name]):
            raise LooseningError(f"limit {name} may only get stricter than {limits[name].value}")
        limits[name] = wanted
    return replace(table, limits=limits)


def loosenings(before: RuleTable, after: RuleTable) -> list[str]:
    """Every way `after` is less strict than `before`, in words, for an approval request."""
    found = [
        f"limit {name}: {limit.bound} {limit.value} -> {after.limits[name].value}"
        for name, limit in before.limits.items()
        if name in after.limits and after.limits[name].is_looser_than(limit)
    ]
    found += [
        f"limit {name} removed" for name in sorted(before.limits.keys() - after.limits.keys())
    ]
    found += [f"ban {ban} lifted" for ban in sorted(before.bans - after.bans)]
    found += [
        f"short name allowed: {name}" for name in sorted(after.allowed_short - before.allowed_short)
    ]
    found += [
        f"banned word allowed: {word}" for word in sorted(before.banned_words - after.banned_words)
    ]
    return found
