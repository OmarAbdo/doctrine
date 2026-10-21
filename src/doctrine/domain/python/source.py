"""Rules on Python source that the standard linters don't cover: function length in lines, names
made of words, suppression comments, imports per module, interface size, composition over
inheritance and a domain that depends on nothing outside itself."""

import ast
import re
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from doctrine.domain.rules.findings import Finding
from doctrine.domain.rules.names import NamePolicy

SUPPRESSION = re.compile(
    r"#\s*(noqa|type:\s*ignore|pylint:\s*disable|pragma:\s*no\s*cover|"
    r"mypy:\s*ignore|ruff:\s*noqa)",
    re.IGNORECASE,
)
INTERFACE_BASES = frozenset({"Protocol", "ABC"})
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class SourceLimits:
    function_lines: int
    imports_per_module: int
    interface_methods: int
    names: NamePolicy


def function_length(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def function_findings(path: str, tree: ast.Module, limit: int) -> list[Finding]:
    functions = [node for node in ast.walk(tree) if isinstance(node, FUNCTIONS)]
    return [
        Finding(
            path,
            node.lineno,
            "function_lines",
            f"{node.name} has {function_length(node)} lines; the limit is {limit}",
        )
        for node in functions
        if function_length(node) > limit
    ]


def named_nodes(tree: ast.Module) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, (*FUNCTIONS, ast.ClassDef)):
            yield node.name, node.lineno
        elif isinstance(node, ast.arg) and node.arg not in ("self", "cls"):
            yield node.arg, node.lineno
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            yield node.id, node.lineno


def name_findings(path: str, tree: ast.Module, policy: NamePolicy) -> Iterator[Finding]:
    seen: set[tuple[str, int]] = set()
    for name, line in named_nodes(tree):
        if (name, line) in seen:
            continue
        seen.add((name, line))
        for problem in policy.problems(name):
            yield Finding(path, line, "names", problem)


def suppression_findings(path: str, source: str) -> Iterator[Finding]:
    for number, line in enumerate(source.splitlines(), start=1):
        if SUPPRESSION.search(line):
            yield Finding(
                path, number, "suppression_comments", "fix the code instead of silencing the check"
            )


def import_findings(path: str, tree: ast.Module, limit: int) -> Iterator[Finding]:
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    if len(imports) > limit:
        yield Finding(
            path,
            imports[limit].lineno,
            "imports_per_module",
            f"{len(imports)} imports; the limit is {limit}: split the module",
        )


def base_names(node: ast.ClassDef) -> list[str]:
    return [base.id if isinstance(base, ast.Name) else ast.unparse(base) for base in node.bases]


def classes(tree: ast.Module) -> list[ast.ClassDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def is_interface(node: ast.ClassDef) -> bool:
    return bool(INTERFACE_BASES & set(base_names(node)))


def method_count(node: ast.ClassDef) -> int:
    return sum(isinstance(item, FUNCTIONS) for item in node.body)


def interface_findings(path: str, tree: ast.Module, limit: int) -> list[Finding]:
    return [
        Finding(
            path,
            node.lineno,
            "interface_methods",
            f"{node.name} has {method_count(node)} methods; the limit is {limit}",
        )
        for node in classes(tree)
        if is_interface(node) and method_count(node) > limit
    ]


def module_findings(path: str, source: str, limits: SourceLimits) -> list[Finding]:
    tree = ast.parse(source)
    return [
        *function_findings(path, tree, limits.function_lines),
        *name_findings(path, tree, limits.names),
        *suppression_findings(path, source),
        *import_findings(path, tree, limits.imports_per_module),
        *interface_findings(path, tree, limits.interface_methods),
    ]


def concrete_classes(sources: Mapping[str, str]) -> set[str]:
    return {
        node.name
        for source in sources.values()
        for node in classes(ast.parse(source))
        if not is_interface(node)
    }


def composition_findings(sources: Mapping[str, str]) -> list[Finding]:
    """A project class may implement a port, but never extend another concrete project class."""
    concrete = concrete_classes(sources)
    return [
        Finding(
            path,
            node.lineno,
            "inheritance",
            f"{node.name} inherits from {base}; compose it instead",
        )
        for path, source in sources.items()
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef)
        for base in base_names(node)
        if base in concrete
    ]


def imported_modules(tree: ast.Module) -> Iterator[tuple[str, int]]:
    for node in tree.body:
        if isinstance(node, ast.Import):
            yield from ((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module, node.lineno


def domain_import_findings(path: str, source: str, package: str) -> list[Finding]:
    allowed_own = f"{package}.domain"
    findings = []
    for module, line in imported_modules(ast.parse(source)):
        top = module.split(".")[0]
        own = top == package and (module == allowed_own or module.startswith(allowed_own + "."))
        if not own and top not in sys.stdlib_module_names:
            findings.append(
                Finding(path, line, "domain_purity", f"the domain may not import {module}")
            )
    return findings
