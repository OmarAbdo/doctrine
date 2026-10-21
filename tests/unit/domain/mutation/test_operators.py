from textwrap import dedent

from doctrine.domain.mutation.operators import Mutant, mutants

SOURCE = dedent("""\
    def adult(age: int) -> bool:
        return age >= 18


    def label(score: int, strict: bool) -> str:
        if strict and score > 90:
            return "top"
        return "other"
""")


def descriptions(found: list[Mutant]) -> list[str]:
    return [f"{mutant.line}: {mutant.description}" for mutant in found]


def test_each_mutant_changes_one_thing_on_the_lines_asked_for() -> None:
    assert descriptions(mutants(SOURCE, lines={2})) == [
        "2: return value became None",
        "2: >= became <",
        "2: 18 became 19",
    ]


def test_conditions_and_booleans_are_mutated() -> None:
    assert descriptions(mutants(SOURCE, lines={6})) == [
        "6: and became or",
        "6: > became <=",
        "6: 90 became 91",
    ]


def test_a_mutant_is_valid_python_that_differs_from_the_source() -> None:
    for mutant in mutants(SOURCE, lines={2, 6, 7}):
        compile(mutant.source, "mutant.py", "exec")
        assert mutant.source != SOURCE


def test_lines_outside_the_change_are_left_alone() -> None:
    assert mutants(SOURCE, lines={4}) == []


def test_flags_and_negations_are_flipped() -> None:
    source = "def ready(done: bool) -> bool:\n    return not done or False\n"
    assert descriptions(mutants(source, lines={2})) == [
        "2: return value became None",
        "2: or became and",
        "2: not removed",
        "2: False became True",
    ]
