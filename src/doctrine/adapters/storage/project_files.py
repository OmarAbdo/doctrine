"""A doctrine project on disk: its root, contract, rule table, work items and source files."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from doctrine.application.check import ServiceSources
from doctrine.domain.governance.contract import Contract, Service, parse_contract
from doctrine.domain.governance.work_item import WorkItem, parse_work_item
from doctrine.domain.rules.table import RuleTable, parse_rule_table, tighten

CONTRACT_FILE = "doctrine.toml"
DOCTRINE_HOME = Path(__file__).resolve().parents[4]
RULE_TABLE_FILE = DOCTRINE_HOME / "rules" / "rules.toml"
SKIPPED_FOLDERS = frozenset({"__pycache__", ".venv", ".mypy_cache", ".ruff_cache", ".pytest_cache"})


def find_root(start: Path) -> Path | None:
    for folder in (start, *start.parents):
        if (folder / CONTRACT_FILE).is_file():
            return folder
    return None


def read_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def base_rule_table() -> RuleTable:
    return parse_rule_table(read_toml(RULE_TABLE_FILE))


@dataclass(frozen=True)
class Project:
    root: Path
    contract: Contract

    @classmethod
    def load(cls, root: Path) -> "Project":
        return cls(root=root, contract=parse_contract(read_toml(root / CONTRACT_FILE)))

    @property
    def rules(self) -> RuleTable:
        return tighten(base_rule_table(), self.contract.limits)

    def work_item(self, item_id: str) -> WorkItem | None:
        matches = sorted((self.root / "work").glob(f"{item_id}-*.toml"))
        return parse_work_item(read_toml(matches[0])) if matches else None

    def next_item_id(self) -> str:
        numbers = [
            int(path.name.split("-", 1)[0])
            for path in (self.root / "work").glob("*-*.toml")
            if path.name.split("-", 1)[0].isdigit()
        ]
        return str(max(numbers, default=0) + 1)

    def python_files(self, folder: Path) -> list[Path]:
        return sorted(
            path
            for path in folder.rglob("*.py")
            if not SKIPPED_FOLDERS & set(path.relative_to(self.root).parts)
        )

    def sources(self, service: Service) -> ServiceSources:
        package_folder = self.root / service.path
        parent = package_folder.parent
        modules = {
            path.relative_to(parent).as_posix(): path.read_text(encoding="utf-8")
            for path in self.python_files(package_folder)
        }
        tests = {
            path.relative_to(self.root).as_posix(): path.read_text(encoding="utf-8")
            for path in self.python_files(self.root / service.tests)
        }
        return ServiceSources(modules=modules, tests=tests)
