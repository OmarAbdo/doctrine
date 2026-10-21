from doctrine.application.mutation import ChangedModule, MutationReport, run_mutants, spread

SOURCE = "def adult(age: int) -> bool:\n    return age >= 18\n"


def test_a_capped_sample_is_spread_over_the_whole_list() -> None:
    assert spread(list(range(10)), limit=4) == [0, 3, 6, 9]
    assert spread([1, 2], limit=4) == [1, 2]


def test_mutants_the_tests_catch_are_killed_and_the_rest_survive() -> None:
    changed = [ChangedModule(path="src/app/age.py", source=SOURCE, lines=frozenset({2}))]

    def tests_fail(path: str, mutated: str) -> bool:
        """These pretend tests catch the empty return and the changed constant only."""
        return "None" in mutated or "19" in mutated

    report = run_mutants(changed, limit=10, tests_fail=tests_fail)
    assert report == MutationReport(total=3, survivors=("src/app/age.py:2 >= became <",))
    assert report.score == 2 / 3


def test_no_changed_lines_means_nothing_to_score() -> None:
    report = run_mutants([], limit=10, tests_fail=lambda path, mutated: True)
    assert report.total == 0
    assert report.score == 1.0
