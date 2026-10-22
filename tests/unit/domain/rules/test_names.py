import pytest

from doctrine.domain.rules.names import NamePolicy, words

POLICY = NamePolicy(
    min_length=3,
    allowed_short=frozenset({"i", "id"}),
    banned_words=frozenset({"tmp", "res", "cfg"}),
)


@pytest.mark.parametrize(
    ("name", "parts"),
    [
        ("job_title", ["job", "title"]),
        ("jobTitle", ["job", "title"]),
        ("HTTPClient", ["http", "client"]),
        ("_private_name", ["private", "name"]),
        ("MAX_RETRIES", ["max", "retries"]),
    ],
)
def test_a_name_splits_into_its_words(name: str, parts: list[str]) -> None:
    assert words(name) == parts


def test_a_descriptive_name_has_no_problem() -> None:
    assert POLICY.problems("application_count") == []


def test_a_short_name_is_a_problem_unless_allowed() -> None:
    assert POLICY.problems("r") == ["'r' is shorter than 3 characters"]
    assert POLICY.problems("id") == []


def test_a_banned_abbreviation_is_a_problem_anywhere_in_the_name() -> None:
    assert POLICY.problems("tmp_file") == ["'tmp_file' uses the abbreviation 'tmp'"]
    assert POLICY.problems("httpRes") == ["'httpRes' uses the abbreviation 'res'"]


def test_python_special_methods_are_named_by_the_language_not_the_project() -> None:
    assert POLICY.problems("__str__") == []
