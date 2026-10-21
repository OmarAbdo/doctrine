import pytest

from doctrine.domain.rules.table import Limit, LooseningError, loosenings, parse_rule_table, tighten

TABLE = {
    "limits": {"function_lines": {"max": 40}, "name_length": {"min": 3}},
    "bans": {"broad_catch": True, "print_statements": False},
    "names": {"allowed_short": ["i", "id"], "banned_words": ["tmp", "res"]},
}


def test_a_table_reads_its_limits_bans_and_names() -> None:
    table = parse_rule_table(TABLE)
    assert table.limit("function_lines") == 40
    assert table.limit("name_length") == 3
    assert table.bans == frozenset({"broad_catch"})
    assert table.allowed_short == frozenset({"i", "id"})
    assert table.banned_words == frozenset({"tmp", "res"})


def test_a_limit_needs_exactly_one_bound() -> None:
    with pytest.raises(ValueError, match="function_lines"):
        parse_rule_table({"limits": {"function_lines": {"max": 40, "min": 1}}})


def test_lowering_a_max_or_raising_a_min_is_tighter() -> None:
    assert (
        Limit("function_lines", "max", 30).is_looser_than(Limit("function_lines", "max", 40))
        is False
    )
    assert (
        Limit("function_lines", "max", 50).is_looser_than(Limit("function_lines", "max", 40))
        is True
    )
    assert Limit("name_length", "min", 2).is_looser_than(Limit("name_length", "min", 3)) is True


def test_a_project_may_tighten_a_limit() -> None:
    table = tighten(parse_rule_table(TABLE), {"function_lines": 30})
    assert table.limit("function_lines") == 30


def test_a_project_may_not_loosen_a_limit_by_itself() -> None:
    with pytest.raises(LooseningError, match="function_lines"):
        tighten(parse_rule_table(TABLE), {"function_lines": 60})


def test_an_unknown_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="no_such_rule"):
        tighten(parse_rule_table(TABLE), {"no_such_rule": 1})


def test_loosenings_lists_every_limit_that_got_looser_and_every_ban_dropped() -> None:
    before = parse_rule_table(TABLE)
    after = parse_rule_table(
        {
            "limits": {"function_lines": {"max": 60}, "name_length": {"min": 4}},
            "bans": {"broad_catch": False},
            "names": {"allowed_short": ["i", "id", "q"], "banned_words": ["tmp"]},
        }
    )
    assert loosenings(before, after) == [
        "limit function_lines: max 40 -> 60",
        "ban broad_catch lifted",
        "short name allowed: q",
        "banned word allowed: res",
    ]
