from doctrine.application.selftest import (
    SelftestScore,
    attack_misses,
    sample_detections,
    tool_codes_by_file,
)
from doctrine.domain.rules.table import parse_rule_table

RULES = parse_rule_table(
    {
        "limits": {
            "function_lines": {"max": 40},
            "imports_per_module": {"max": 12},
            "interface_methods": {"max": 5},
            "name_length": {"min": 3},
        },
        "names": {"allowed_short": ["i"], "banned_words": ["tmp"]},
    }
)


def test_doctrine_rules_are_detected_in_a_sample() -> None:
    found = sample_detections("short_name.py", "def total(r: int) -> int:\n    return r\n", RULES)
    assert "names" in found


def test_a_sample_is_also_judged_as_domain_code() -> None:
    found = sample_detections("domain_purity.py", "import requests\n", RULES)
    assert "domain_purity" in found


def test_linter_output_is_grouped_by_file_and_code() -> None:
    output = (
        "complexity.py:1:5: C901 `grade` is too complex (10 > 8)\n"
        "nesting.py:4:12: R1702: Too many nested blocks (4/3) (too-many-nested-blocks)\n"
        "Found 2 errors.\n"
    )
    assert tool_codes_by_file(output) == {"complexity.py": {"C901"}, "nesting.py": {"R1702"}}


def test_every_attack_must_be_refused() -> None:
    attacks = {
        "shell": [{"command": "git commit --no-verify -m x"}, {"command": "git status"}],
        "edit": [{"path": ".doctrine/state.json"}],
    }
    assert attack_misses(attacks) == ["shell: git status"]


def test_the_score_is_the_share_caught() -> None:
    score = SelftestScore(total=20, missed=["a", "b"])
    assert score.share == 0.9
