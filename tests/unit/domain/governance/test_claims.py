import pytest

from doctrine.domain.governance.claims import success_claims


@pytest.mark.parametrize(
    ("message", "claim"),
    [
        ("The login bug is fixed.", "fixed"),
        ("I verified it on the real data.", "verified"),
        ("All tests pass now.", "pass"),
        ("Search works again.", "works"),
        ("Done: the importer reads both files.", "done"),
        ("Root cause found and resolved.", "resolved"),
    ],
)
def test_a_success_claim_is_found(message: str, claim: str) -> None:
    assert claim in success_claims(message)


@pytest.mark.parametrize(
    "message",
    [
        "This is not fixed yet.",
        "I haven't verified it on real data.",
        "It's unverified: the run needs your login.",
        "The tests don't pass yet; two fail on dates.",
        "Nothing here is done until the run proves it.",
    ],
)
def test_a_negated_claim_is_no_claim(message: str) -> None:
    assert success_claims(message) == []
