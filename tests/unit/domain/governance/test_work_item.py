import pytest

from doctrine.domain.governance.work_item import WorkItem, parse_work_item

ITEM = {
    "id": "7",
    "title": "Search by city",
    "kind": "feature",
    "scope": ["src/jobs/search/**", "src/jobs/domain/city.py"],
}


def test_an_item_reads_its_parts() -> None:
    item = parse_work_item(ITEM)
    assert item == WorkItem(
        id="7",
        title="Search by city",
        kind="feature",
        scope=("src/jobs/search/**", "src/jobs/domain/city.py"),
    )
    assert item.branch == "item/7-search-by-city"


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="kind"):
        parse_work_item({**ITEM, "kind": "misc"})


def test_files_outside_the_scope_are_listed_but_tests_and_items_are_always_in() -> None:
    item = parse_work_item(ITEM)
    changed = [
        "src/jobs/search/query.py",
        "src/jobs/domain/city.py",
        "src/jobs/mail/send.py",
        "tests/unit/test_query.py",
        "work/7-search-by-city.toml",
        "README.md",
    ]
    assert item.out_of_scope(changed) == ["src/jobs/mail/send.py", "README.md"]


@pytest.mark.parametrize(
    ("kind", "red_first"),
    [
        ("feature", True),
        ("fix", True),
        ("restore", True),
        ("refactor", False),
        ("chore", False),
    ],
)
def test_features_and_fixes_start_with_a_failing_test(kind: str, red_first: bool) -> None:
    assert parse_work_item({**ITEM, "kind": kind}).red_first is red_first


@pytest.mark.parametrize("pattern", ["**", "*.py", "**/*.py"])
def test_a_scope_must_name_a_folder_or_file_not_everything(pattern: str) -> None:
    with pytest.raises(ValueError, match="scope"):
        parse_work_item({**ITEM, "scope": [pattern]})


def test_an_item_needs_a_scope() -> None:
    with pytest.raises(ValueError, match="scope"):
        parse_work_item({**ITEM, "scope": []})
