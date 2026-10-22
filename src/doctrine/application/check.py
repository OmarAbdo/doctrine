"""`doctrine check` for a Python service: doctrine's own source rules plus the standard tools."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from doctrine.application.ports import ToolResult, ToolRunner
from doctrine.application.python_tools import tool_commands
from doctrine.domain.governance.contract import Service
from doctrine.domain.rules.findings import Finding
from doctrine.domain.rules.names import NamePolicy
from doctrine.domain.python.layout import (
    folder_findings,
    hexagonal_findings,
    kind_of_test_findings,
    layer_findings,
)
from doctrine.domain.python.source import (
    SourceLimits,
    composition_findings,
    domain_import_findings,
    module_findings,
)
from doctrine.domain.rules.table import RuleTable

NO_TESTS_COLLECTED = 5  # pytest's exit code when it found no tests


@dataclass(frozen=True)
class ServiceSources:
    """Source text by path: modules relative to the package's parent folder, tests to the root."""

    modules: Mapping[str, str]
    tests: Mapping[str, str]


@dataclass(frozen=True)
class CheckReport:
    findings: list[Finding] = field(default_factory=list)
    tools: list[ToolResult] = field(default_factory=list)

    @property
    def failed_tools(self) -> list[ToolResult]:
        return [result for result in self.tools if not result.passed]

    @property
    def passed(self) -> bool:
        return not self.findings and not self.failed_tools


def name_policy(rules: RuleTable) -> NamePolicy:
    return NamePolicy(rules.limit("name_length"), rules.allowed_short, rules.banned_words)


def source_limits(rules: RuleTable) -> SourceLimits:
    return SourceLimits(
        function_lines=rules.limit("function_lines"),
        imports_per_module=rules.limit("imports_per_module"),
        interface_methods=rules.limit("interface_methods"),
        names=name_policy(rules),
    )


def file_name_findings(paths: list[str], policy: NamePolicy) -> list[Finding]:
    stems = [(path, PurePosixPath(path).stem) for path in paths]
    return [
        Finding(path, 1, "names", problem)
        for path, stem in stems
        if not stem.startswith("__")
        for problem in policy.problems(stem)
    ]


def layered_findings(package: str, sources: ServiceSources) -> list[Finding]:
    findings = []
    for path, source in sources.modules.items():
        if path.startswith(f"{package}/domain/"):
            findings += domain_import_findings(path, source, package)
        elif path.startswith(f"{package}/application/"):
            findings += layer_findings(path, source, package)
    return findings


def source_findings(service: Service, rules: RuleTable, sources: ServiceSources) -> list[Finding]:
    package, modules = service.package, sorted(sources.modules)
    findings = [
        finding
        for path in modules
        for finding in module_findings(path, sources.modules[path], source_limits(rules))
    ]
    findings += composition_findings(sources.modules)
    findings += file_name_findings(modules, name_policy(rules))
    findings += folder_findings(modules, rules.limit("modules_per_folder"))
    if service.architecture == "hexagonal":
        findings += hexagonal_findings(package, modules)
        findings += layered_findings(package, sources)
    return findings + kind_of_test_findings(package, modules, sources.tests)


def check_python_service(
    service: Service, rules: RuleTable, sources: ServiceSources, runner: ToolRunner
) -> CheckReport:
    commands = tool_commands(rules, service)
    tools = [judged(runner.run(command.name, command.arguments)) for command in commands]
    return CheckReport(findings=source_findings(service, rules, sources), tools=tools)


def judged(result: ToolResult) -> ToolResult:
    """A service with no tests yet (fresh from `doctrine init`) makes pytest collect nothing. That
    is no failure: the test_kinds rule already demands a test for every module."""
    if result.name == "pytest" and result.exit_code == NO_TESTS_COLLECTED:
        return ToolResult(name=result.name, passed=True, output=result.output)
    return result
