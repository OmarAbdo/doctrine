"""`doctrine selftest`, doctrine's own outcome: the share of bad samples and bypasses it catches.

The samples and attacks are data (samples/), so every escape found later becomes one more case.
"""

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from doctrine.application.check import source_limits
from doctrine.application.guard import Situation, ToolEvent, decide_tool_use
from doctrine.domain.governance.work_item import WorkItem
from doctrine.domain.python.source import (
    composition_findings,
    domain_import_findings,
    module_findings,
)
from doctrine.domain.rules.table import RuleTable

TOOL_LINE = re.compile(r"^(?P<path>[\w./\\-]+\.py):\d+:\d+: (?P<code>[A-Z]+\d+)")
ROOT = "D:/selftest"
ATTACK_SITUATION = Situation(
    root=ROOT,
    source_roots=("src/project",),
    branch="item/1-inside",
    item=WorkItem(id="1", title="Inside", kind="feature", scope=("src/project/domain/inside/**",)),
    red_seen=True,
    line_stopped=False,
    unchecked_changes=False,
)


@dataclass(frozen=True)
class SelftestScore:
    total: int
    missed: list[str] = field(default_factory=list)

    @property
    def share(self) -> float:
        return (self.total - len(self.missed)) / self.total if self.total else 0.0


def sample_detections(name: str, source: str, rules: RuleTable) -> set[str]:
    """The doctrine rules a sample breaks, judged as ordinary code and as domain code."""
    findings = module_findings(name, source, source_limits(rules))
    findings += composition_findings({name: source})
    findings += domain_import_findings(f"project/domain/{name}", source, package="project")
    return {finding.rule for finding in findings}


def tool_codes_by_file(output: str) -> dict[str, set[str]]:
    codes: dict[str, set[str]] = defaultdict(set)
    for line in output.splitlines():
        match = TOOL_LINE.match(line.strip())
        if match:
            codes[match.group("path").replace("\\", "/")].add(match.group("code"))
    return dict(codes)


def attack_misses(attacks: Mapping[str, Sequence[Mapping[str, str]]]) -> list[str]:
    misses = []
    for case in attacks.get("shell", []):
        event = ToolEvent(tool="Bash", tool_input={"command": case["command"]})
        if decide_tool_use(event, ATTACK_SITUATION).allowed:
            misses.append(f"shell: {case['command']}")
    for case in attacks.get("edit", []):
        path = case["path"] if ":" in case["path"] else f"{ROOT}/{case['path']}"
        event = ToolEvent(tool="Write", tool_input={"file_path": path})
        if decide_tool_use(event, ATTACK_SITUATION).allowed:
            misses.append(f"edit: {case['path']}")
    return misses
