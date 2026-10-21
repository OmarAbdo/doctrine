import pytest

from doctrine.domain.evals.cases import EvalCase, parse_cases
from doctrine.domain.evals.scoring import EvalRun, score_outputs

LINES = [
    {"id": "senior-python", "input": "Senior Python engineer, Berlin", "expected": "apply"},
    {"id": "sales-role", "input": "Account executive", "expected": ["skip", "no"]},
    {"id": "german-c2", "input": "Muttersprache Deutsch", "expected": "skip"},
]


def test_cases_read_their_input_and_every_acceptable_answer() -> None:
    cases = parse_cases(LINES)
    assert cases[1] == EvalCase(id="sales-role", input="Account executive", expected=("skip", "no"))


def test_a_case_needs_an_id_and_an_expected_answer() -> None:
    with pytest.raises(ValueError, match="line 1"):
        parse_cases([{"input": "no id"}])
    with pytest.raises(ValueError, match="no-answer"):
        parse_cases([{"id": "no-answer", "input": "x"}])


def test_case_ids_are_unique() -> None:
    with pytest.raises(ValueError, match="senior-python"):
        parse_cases([LINES[0], LINES[0]])


def test_an_output_passes_when_it_matches_an_acceptable_answer_ignoring_case_and_spaces() -> None:
    outputs = {"senior-python": " Apply ", "sales-role": "no", "german-c2": "apply"}
    run = score_outputs(parse_cases(LINES), outputs)
    assert run == EvalRun(total=3, failures=("german-c2",))
    assert run.score == pytest.approx(2 / 3)


def test_a_missing_output_is_a_failure() -> None:
    run = score_outputs(parse_cases(LINES), {"senior-python": "apply"})
    assert run.failures == ("sales-role", "german-c2")


def test_an_empty_eval_set_scores_zero() -> None:
    assert score_outputs([], {}).score == 0.0
