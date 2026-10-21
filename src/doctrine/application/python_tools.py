"""The standard Python tools, configured from the rule table so no config file can drift from it."""

from collections.abc import Iterator
from dataclasses import dataclass

from doctrine.domain.governance.contract import Service
from doctrine.domain.rules.table import RuleTable

BASE_RUFF_RULES = (
    "E",
    "F",
    "W",
    "B",
    "C90",
    "N",
    "UP",
    "SIM",
    "RET",
    "PERF",
    "PL",
    "ARG",
    "ERA",
    "PGH004",
    "RUF100",
)
BAN_RUFF_RULES = {
    "broad_catch": ("BLE", "E722", "S110"),
    "flag_arguments": ("FBT",),
    "print_statements": ("T20",),
    "missing_timeouts": ("S113",),
}


@dataclass(frozen=True)
class ToolCommand:
    name: str
    arguments: list[str]


def ruff_rules(rules: RuleTable) -> list[str]:
    selected = list(BASE_RUFF_RULES)
    for ban, codes in BAN_RUFF_RULES.items():
        if ban in rules.bans:
            selected += codes
    return selected


def ruff_settings(rules: RuleTable) -> Iterator[str]:
    settings = {
        "lint.mccabe.max-complexity": rules.limit("complexity"),
        "lint.pylint.max-args": rules.limit("parameters"),
        "lint.pylint.max-positional-args": rules.limit("parameters"),
        "lint.pylint.max-branches": rules.limit("complexity"),
        "lint.pylint.max-public-methods": rules.limit("public_methods"),
    }
    for key, value in settings.items():
        yield from ("--config", f"{key}={value}")
    yield from ("--config", 'lint.per-file-ignores={"tests/**" = ["PLR2004", "FBT001", "ARG"]}')


def ruff_check(rules: RuleTable, paths: list[str]) -> ToolCommand:
    arguments = [
        "check",
        "--no-cache",
        "--output-format=concise",
        f"--line-length={rules.limit('line_length')}",
        f"--select={','.join(ruff_rules(rules))}",
        *ruff_settings(rules),
        *paths,
    ]
    return ToolCommand("ruff", arguments)


def pylint_check(rules: RuleTable, paths: list[str]) -> ToolCommand:
    """Only what ruff lacks: nested blocks, module length and public methods."""
    return ToolCommand(
        "pylint",
        [
            "--disable=all",
            "--enable=too-many-nested-blocks,too-many-lines,too-many-public-methods",
            f"--max-nested-blocks={rules.limit('nesting')}",
            f"--max-module-lines={rules.limit('file_lines')}",
            f"--max-public-methods={rules.limit('public_methods')}",
            "--score=n",
            *paths,
        ],
    )


def tool_commands(rules: RuleTable, service: Service) -> list[ToolCommand]:
    paths = [service.path, service.tests]
    return [
        ruff_check(rules, paths),
        ToolCommand(
            "ruff-format",
            [
                "format",
                "--no-cache",
                f"--line-length={rules.limit('line_length')}",
                "--check",
                service.path,
            ],
        ),
        pylint_check(rules, paths),
        ToolCommand("mypy", ["--strict", "--explicit-package-bases", service.path]),
        ToolCommand("pytest", ["-q", "-p", "no:cacheprovider", service.tests]),
    ]
