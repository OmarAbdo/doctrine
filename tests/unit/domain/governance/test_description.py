from doctrine.domain.governance.description import REQUIRED, description_problems

COMPLETE = """## What changed
The scope gate counts every changed line.

## Why
A rewrite of 300 lines counted 0.

## Proof
tests/integration/test_ci.py fails on the code before.

## Not verified
Nothing: everything above ran in CI.
"""


def test_a_complete_description_has_no_problems() -> None:
    assert description_problems(COMPLETE) == []


def test_every_missing_section_is_named() -> None:
    assert description_problems("Fixes the gate.") == [
        f"no '## {name}' section" for name in REQUIRED
    ]


def test_an_empty_or_placeholder_section_counts_as_missing() -> None:
    body = COMPLETE.replace("Nothing: everything above ran in CI.", "TODO").replace(
        "A rewrite of 300 lines counted 0.", ""
    )
    assert description_problems(body) == [
        "the '## Why' section is empty",
        "the '## Not verified' section is empty",
    ]


def test_the_untouched_template_counts_as_empty() -> None:
    template = "".join(f"## {name}\n<!-- what to write here -->\n\n" for name in REQUIRED)
    assert description_problems(template) == [
        f"the '## {name}' section is empty" for name in REQUIRED
    ]


def test_headings_match_whatever_their_case() -> None:
    assert description_problems(COMPLETE.replace("## Proof", "## proof")) == []
