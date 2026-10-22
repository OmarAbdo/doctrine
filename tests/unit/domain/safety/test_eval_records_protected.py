"""The CI gate trusts an AI task's recorded runs, so only `doctrine eval run` may write them."""

from doctrine.domain.safety.command_policy import CommandContext, judge_command
from doctrine.domain.safety.protected import is_protected

ON_ITEM = CommandContext(current_branch="item/3-fit", in_project=True)


def test_recorded_runs_are_protected_but_eval_sets_are_not() -> None:
    assert is_protected("D:/work/jobs/evals/fit/results.jsonl", "evals/fit/results.jsonl")
    assert is_protected(r"D:\work\jobs\evals\fit\results.jsonl")
    assert not is_protected("D:/work/jobs/evals/fit/cases.jsonl", "evals/fit/cases.jsonl")
    assert not is_protected("D:/work/jobs/src/jobs/results.jsonl", "src/jobs/results.jsonl")


def test_a_shell_write_to_recorded_runs_is_refused() -> None:
    forged = """echo '{"score": 1.0}' >> evals/fit/results.jsonl"""
    assert judge_command(forged, ON_ITEM).rule == "protected-path"
    assert judge_command("cat evals/fit/results.jsonl", ON_ITEM).allowed
    assert judge_command("doctrine eval run fit", ON_ITEM).allowed
