"""#59: the first item records the metric, as the docs say, and its own scope gate refused the
recorded value."""

from doctrine.domain.governance.work_item import parse_work_item

ITEM = {"id": "1", "title": "Outcome metric", "kind": "feature", "scope": ["doctrine.toml"]}


def test_a_recorded_metric_is_in_every_items_scope() -> None:
    item = parse_work_item(ITEM)
    assert item.covers("metrics/outcome.jsonl")
    assert item.out_of_scope(["metrics/outcome.jsonl", "doctrine.toml"]) == []
