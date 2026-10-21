"""Rules on how a Python service is laid out: hexagonal layers, folder size and a test of the right
kind for every module."""

import ast
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from pathlib import PurePosixPath

from doctrine.domain.rules.findings import Finding
from doctrine.domain.python.source import imported_modules

HEXAGONAL_PARTS = frozenset({"domain", "application", "adapters"})
PACKAGE_FILES = frozenset({"__init__.py", "__main__.py"})


def layer_findings(path: str, source: str, package: str) -> list[Finding]:
    forbidden = f"{package}.adapters"
    return [
        Finding(path, line, "layers", f"the application may not import {module}")
        for module, line in imported_modules(ast.parse(source))
        if module == forbidden or module.startswith(forbidden + ".")
    ]


def top_level_part(package: str, path: str) -> tuple[str, bool] | None:
    """(name, is_folder) of the part of `package` that `path` sits in, or None outside it."""
    parts = PurePosixPath(path).relative_to(package).parts if path.startswith(package + "/") else ()
    if not parts:
        return None
    return parts[0], len(parts) > 1


def hexagonal_findings(package: str, files: Sequence[str]) -> list[Finding]:
    reported: list[str] = []
    for path in files:
        part = top_level_part(package, path)
        if part is None or part[0] in HEXAGONAL_PARTS or part[0] in PACKAGE_FILES:
            continue
        where = f"{package}/{part[0]}"
        if where not in reported:
            reported.append(where)
    return [
        Finding(
            where,
            1,
            "architecture",
            f"{where}: a hexagonal package holds only domain/, application/ and adapters/",
        )
        for where in reported
    ]


def folder_findings(files: Sequence[str], limit: int) -> list[Finding]:
    modules = Counter(
        str(PurePosixPath(path).parent)
        for path in files
        if PurePosixPath(path).name not in PACKAGE_FILES
    )
    return [
        Finding(
            folder,
            1,
            "modules_per_folder",
            f"{folder} holds {count} modules; the limit is {limit}: "
            "group them into sub-folders by responsibility",
        )
        for folder, count in sorted(modules.items())
        if count > limit
    ]


def module_name(path: str) -> str:
    return str(PurePosixPath(path).with_suffix("")).replace("/", ".")


def imports_of(source: str) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def unit_tests_on_adapters(package: str, tests: Mapping[str, str]) -> Iterator[Finding]:
    adapters = f"{package}.adapters"
    for path, source in tests.items():
        if not path.startswith("tests/unit/"):
            continue
        for module in sorted(imports_of(source)):
            if module.startswith(adapters + ".") and module.count(".") == adapters.count(".") + 1:
                yield Finding(
                    path,
                    1,
                    "test_kinds",
                    f"{path}: a unit test may not import {module} (use tests/integration)",
                )


def untested_modules(modules: Sequence[str], tests: Mapping[str, str]) -> Iterator[Finding]:
    imported = {
        kind: set().union(
            *(
                imports_of(source)
                for path, source in tests.items()
                if path.startswith(f"tests/{kind}/")
            )
        )
        for kind in ("unit", "integration")
    }
    for path in modules:
        if PurePosixPath(path).name in PACKAGE_FILES:
            continue
        kind = "integration" if "/adapters/" in path else "unit"
        if module_name(path) not in imported[kind]:
            yield Finding(path, 1, "test_kinds", f"{path} has no {kind} test that imports it")


def kind_of_test_findings(
    package: str, modules: Sequence[str], tests: Mapping[str, str]
) -> list[Finding]:
    return [*unit_tests_on_adapters(package, tests), *untested_modules(modules, tests)]
