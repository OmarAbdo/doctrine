from collections.abc import Sequence

from doctrine.application.check import ServiceSources, check_python_service
from doctrine.application.ports import ToolResult
from doctrine.application.python_tools import tool_commands
from doctrine.domain.governance.contract import Service
from doctrine.domain.rules.table import parse_rule_table

RULES = parse_rule_table(
    {
        "limits": {
            "function_lines": {"max": 40},
            "complexity": {"max": 8},
            "nesting": {"max": 3},
            "parameters": {"max": 4},
            "file_lines": {"max": 300},
            "line_length": {"max": 100},
            "public_methods": {"max": 7},
            "imports_per_module": {"max": 12},
            "interface_methods": {"max": 5},
            "modules_per_folder": {"max": 10},
            "name_length": {"min": 3},
        },
        "bans": {
            "broad_catch": True,
            "flag_arguments": True,
            "print_statements": True,
            "missing_timeouts": True,
        },
        "names": {"allowed_short": ["i"], "banned_words": ["tmp"]},
    }
)
SERVICE = Service(name="core", path="src/jobs", profile="python", architecture="hexagonal")


def test_the_linters_get_their_limits_from_the_rule_table() -> None:
    commands = {command.name: command.arguments for command in tool_commands(RULES, SERVICE)}
    ruff = " ".join(commands["ruff"])
    assert "lint.mccabe.max-complexity=8" in ruff
    assert "lint.pylint.max-args=4" in ruff
    assert "--line-length=100" in ruff
    assert "BLE" in ruff and "FBT" in ruff and "T20" in ruff and "S113" in ruff
    assert "--max-nested-blocks=3" in commands["pylint"]
    assert "--max-module-lines=300" in commands["pylint"]
    assert "--strict" in commands["mypy"]
    assert commands["ruff-format"][-2:] == ["--check", "src/jobs"]


def test_a_lifted_ban_drops_its_linter_rules() -> None:
    relaxed = parse_rule_table(
        {
            "limits": {key: {limit.bound: limit.value} for key, limit in RULES.limits.items()},
            "bans": {"broad_catch": False},
        }
    )
    ruff = " ".join(
        next(
            command.arguments
            for command in tool_commands(relaxed, SERVICE)
            if command.name == "ruff"
        )
    )
    assert "BLE" not in ruff


class FakeRunner:
    def __init__(self, failing: Sequence[str] = ()) -> None:
        self.failing, self.ran = set(failing), []

    def run(self, name: str, arguments: Sequence[str]) -> ToolResult:
        self.ran.append(name)
        failed = name in self.failing
        return ToolResult(name=name, passed=not failed, output="boom" if failed else "")


SOURCES = ServiceSources(
    modules={
        "jobs/__init__.py": "",
        "jobs/domain/__init__.py": "",
        "jobs/domain/job.py": "def job_title(name: str) -> str:\n    return name\n",
    },
    tests={"tests/unit/test_job.py": "from jobs.domain.job import job_title\n"},
)


def test_a_clean_service_passes_when_every_tool_passes() -> None:
    runner = FakeRunner()
    report = check_python_service(SERVICE, RULES, SOURCES, runner)
    assert report.passed
    assert set(runner.ran) == {"ruff", "ruff-format", "pylint", "mypy", "pytest"}


def test_a_failing_tool_fails_the_check() -> None:
    report = check_python_service(SERVICE, RULES, SOURCES, FakeRunner(failing=["mypy"]))
    assert not report.passed
    assert [result.name for result in report.failed_tools] == ["mypy"]


def test_source_findings_fail_the_check() -> None:
    sources = ServiceSources(
        modules={**SOURCES.modules, "jobs/domain/tmp.py": "import requests\n"}, tests=SOURCES.tests
    )
    report = check_python_service(SERVICE, RULES, sources, FakeRunner())
    assert not report.passed
    rules = {finding.rule for finding in report.findings}
    assert {"names", "domain_purity", "test_kinds"} <= rules
