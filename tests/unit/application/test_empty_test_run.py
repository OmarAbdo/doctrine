import tomllib
from collections.abc import Sequence
from pathlib import Path

from doctrine.application.check import ServiceSources, check_python_service
from doctrine.application.ports import ToolResult
from doctrine.domain.governance.contract import Service
from doctrine.domain.rules.table import parse_rule_table

TABLE = Path(__file__).resolve().parents[3] / "rules" / "rules.toml"
RULES = parse_rule_table(tomllib.loads(TABLE.read_text(encoding="utf-8")))
SERVICE = Service(name="jobs", path="src/jobs", profile="python", architecture="layered")


class Runner:
    def __init__(self, pytest_output: str) -> None:
        self.pytest_output = pytest_output

    def run(self, name: str, arguments: Sequence[str]) -> ToolResult:
        if name == "pytest":
            code = 5 if self.pytest_output == "no tests ran" else 1
            return ToolResult(name=name, passed=False, output=self.pytest_output, exit_code=code)
        return ToolResult(name=name, passed=True, output="")


def test_no_tests_yet_is_no_failure() -> None:
    """Every module still needs its test: the test_kinds rule says so, not pytest."""
    report = check_python_service(SERVICE, RULES, ServiceSources({}, {}), Runner("no tests ran"))
    assert report.passed


def test_failing_tests_still_fail() -> None:
    report = check_python_service(SERVICE, RULES, ServiceSources({}, {}), Runner("1 failed"))
    assert not report.passed
