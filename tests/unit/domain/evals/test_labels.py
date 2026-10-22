import pytest

from doctrine.domain.evals.labels import Trace, label_row, parse_traces, unlabelled


def test_traces_keep_their_id_or_get_one_from_their_content() -> None:
    traces = parse_traces(
        [
            {"id": "t1", "input": "job ad", "output": "fits"},
            {"input": "other ad", "output": "no fit"},
            {"input": "other ad", "output": "no fit"},
        ]
    )
    assert traces[0] == Trace(id="t1", input="job ad", output="fits")
    assert traces[1].id == traces[2].id != "t1"


def test_a_label_becomes_a_judge_case_with_the_trace_as_its_input() -> None:
    trace = Trace(id="t1", input="job ad", output="fits")
    assert label_row(trace, "fail", "  it ignored the salary ") == {
        "id": "t1",
        "input": {"input": "job ad", "output": "fits"},
        "expected": "fail",
        "note": "it ignored the salary",
    }


def test_a_label_is_pass_or_fail() -> None:
    with pytest.raises(ValueError, match="a label is pass or fail"):
        label_row(Trace(id="t1", input="a", output="b"), "maybe", "")


def test_traces_already_labelled_are_not_shown_again() -> None:
    traces = [Trace(id=name, input=name, output=name) for name in ("a", "b", "c")]
    assert [trace.id for trace in unlabelled(traces, {"b"})] == ["a", "c"]
