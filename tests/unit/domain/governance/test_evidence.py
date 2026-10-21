from doctrine.domain.governance.evidence import Evidence, first_broken_link, item_not_ready, link


def entries() -> list[Evidence]:
    first = link(None, kind="test", outcome="red", item="7", recorded_at="2026-10-21T10:00:00Z")
    second = link(first, kind="test", outcome="green", item="7", recorded_at="2026-10-21T10:05:00Z")
    third = link(
        second, kind="check", outcome="passed", item="7", recorded_at="2026-10-21T10:06:00Z"
    )
    return [first, second, third]


def test_each_entry_carries_the_digest_of_the_one_before() -> None:
    first, second, _ = entries()
    assert first.previous == ""
    assert second.previous == first.digest


def test_an_untouched_chain_has_no_broken_link() -> None:
    assert first_broken_link(entries()) is None


def test_an_edited_entry_breaks_the_chain_where_it_was_edited() -> None:
    chain = entries()
    chain[1] = Evidence(**{**chain[1].as_dict(), "outcome": "red"})
    assert first_broken_link(chain) == 1


def test_a_removed_entry_breaks_the_chain() -> None:
    chain = entries()
    del chain[1]
    assert first_broken_link(chain) == 1


def run(*steps: tuple[str, str]) -> list[Evidence]:
    chain: list[Evidence] = []
    for number, (kind, outcome) in enumerate(steps):
        chain.append(
            link(
                chain[-1] if chain else None,
                kind=kind,
                outcome=outcome,
                item="7",
                recorded_at=f"2026-10-21T10:{number:02d}:00Z",
            )
        )
    return chain


def test_an_item_is_ready_after_red_then_a_passing_check() -> None:
    chain = run(("test", "red"), ("test", "green"), ("check", "passed"))
    assert item_not_ready(chain, "7", red_first=True) is None


def test_an_item_without_a_passing_check_is_not_ready() -> None:
    chain = run(("test", "red"), ("test", "green"))
    assert "doctrine check" in (item_not_ready(chain, "7", red_first=True) or "")


def test_a_red_run_after_the_last_check_makes_the_item_not_ready() -> None:
    chain = run(("test", "red"), ("check", "passed"), ("test", "red"))
    assert "doctrine check" in (item_not_ready(chain, "7", red_first=True) or "")


def test_a_feature_without_a_red_run_is_not_ready() -> None:
    chain = run(("test", "green"), ("check", "passed"))
    assert "failing test" in (item_not_ready(chain, "7", red_first=True) or "")
    assert item_not_ready(chain, "7", red_first=False) is None
