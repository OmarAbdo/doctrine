from doctrine.domain.evals.task import AiTask, ai_task_problems, parse_ai_task

TASK = {"name": "form-answers", "prompt": "prompts/form.md", "command": ["run"], "minimum": 0.9}


def test_a_task_keeps_its_eval_set_and_results_under_its_name() -> None:
    task = parse_ai_task(TASK)
    assert task == AiTask(
        name="form-answers", prompt="prompts/form.md", command=("run",), minimum=0.9
    )
    assert task.cases == "evals/form-answers/cases.jsonl"
    assert task.results == "evals/form-answers/results.jsonl"


def test_every_missing_part_is_named() -> None:
    assert ai_task_problems({"name": "bare"}) == [
        "ai task bare: prompt is missing",
        "ai task bare: command is missing",
        "ai task bare: minimum is missing",
    ]


def test_a_complete_task_has_no_problems() -> None:
    assert ai_task_problems(TASK) == []
