from doctrine.domain.governance.goalposts import eval_label_changes

CASES = [
    {"id": "a", "input": "2+2", "expected": ["4", "four"]},
    {"id": "b", "input": "3+3", "expected": "6"},
]
RESULT = {"prompt": "p1", "cases": "c1", "score": 1.0, "total": 2, "failures": []}


def test_an_eval_sets_expected_answers_are_its_labels() -> None:
    """2026-10-22: the gate read a "label" key that eval cases don't have; any pull request that
    changed an eval set crashed it."""
    after = [{**CASES[0], "expected": ["5"]}, {"id": "c", "input": "1+1", "expected": "2"}]
    assert eval_label_changes(CASES, after) == [
        "eval case a: expected 4 | four -> 5",
        "eval case b removed",
    ]
    assert eval_label_changes(CASES, [*CASES, {"id": "c", "input": "1+1", "expected": "2"}]) == []


def test_recorded_runs_are_not_labels() -> None:
    assert eval_label_changes([RESULT], [RESULT, {**RESULT, "score": 0.5}]) == []
