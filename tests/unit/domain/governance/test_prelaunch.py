"""2026-10-22 (#46): a project that hasn't shipped honestly measures 0, and its first record
stopped its own line. The line arms once a recorded value has reached the stop value."""

from doctrine.domain.governance.contract import Outcome

OUTCOME = Outcome(metric="applications sent per day", command=("x",), baseline=10, stop_below=0.8)


def test_before_launch_no_value_stops_the_line() -> None:
    assert not OUTCOME.launched([0, 0, 3])
    assert not OUTCOME.line_stopped([0, 0, 3])
    assert not OUTCOME.line_stopped([])


def test_after_launch_a_fall_under_the_stop_value_stops_it() -> None:
    assert OUTCOME.launched([0, 9])
    assert not OUTCOME.line_stopped([0, 9, 8])
    assert OUTCOME.line_stopped([0, 9, 7.9])
