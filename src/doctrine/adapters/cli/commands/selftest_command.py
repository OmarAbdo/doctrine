"""`doctrine selftest`: every bad sample and bypass attempt is run; the share caught comes last."""

import shutil
import tempfile
from pathlib import Path

from doctrine.adapters.cli.console import say
from doctrine.adapters.storage.project_files import DOCTRINE_HOME, base_rule_table, read_toml
from doctrine.adapters.tools.subprocess_runner import SubprocessRunner
from doctrine.application.python_tools import pylint_check, ruff_check
from doctrine.application.selftest import (
    SelftestScore,
    attack_misses,
    sample_detections,
    tool_codes_by_file,
)
from doctrine.domain.rules.table import RuleTable

SAMPLES = DOCTRINE_HOME / "samples"


def long_module(rules: RuleTable) -> str:
    lines = rules.limit("file_lines") + 5
    return "".join(f"LINE_{number} = {number}\n" for number in range(lines))


def linter_codes(folder: Path, names: list[str], rules: RuleTable) -> dict[str, set[str]]:
    runner = SubprocessRunner(folder, import_roots=[folder])
    outputs = [
        runner.run("ruff", ruff_check(rules, names).arguments).output,
        runner.run("pylint", pylint_check(rules, names).arguments).output,
    ]
    codes: dict[str, set[str]] = {}
    for output in outputs:
        for name, found in tool_codes_by_file(output).items():
            codes.setdefault(name, set()).update(found)
    return codes


def sample_misses(rules: RuleTable) -> tuple[int, list[str]]:
    expectations = {
        name: str(code)
        for name, code in read_toml(SAMPLES / "python" / "expectations.toml").items()
    }
    with tempfile.TemporaryDirectory(prefix="doctrine-selftest-") as temporary:
        folder = Path(temporary)
        for sample in (SAMPLES / "python").glob("*.py"):
            shutil.copyfile(sample, folder / sample.name)
        (folder / "file_lines.py").write_text(long_module(rules), encoding="utf-8")
        codes = linter_codes(folder, sorted(expectations), rules)
        misses = []
        for name, expected in sorted(expectations.items()):
            source = (folder / name).read_text(encoding="utf-8")
            if expected not in sample_detections(name, source, rules) | codes.get(name, set()):
                misses.append(f"sample {name}: {expected} not caught")
    return len(expectations), misses


def attack_cases() -> dict[str, list[dict[str, str]]]:
    data = read_toml(SAMPLES / "attacks.toml")
    return {
        kind: [{key: str(value) for key, value in case.items()} for case in cases]
        for kind, cases in data.items()
        if isinstance(cases, list)
    }


def selftest_command() -> int:
    total, misses = sample_misses(base_rule_table())
    attacks = attack_cases()
    misses += attack_misses(attacks)
    total += sum(len(cases) for cases in attacks.values())
    score = SelftestScore(total=total, missed=misses)
    for miss in misses:
        say(f"MISSED {miss}")
    say(f"{total - len(misses)} of {total} caught")
    say(f"{score.share:g}")
    return 0
