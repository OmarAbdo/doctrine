import pytest

from doctrine.domain.dependencies.locking import Pin, declared, lock_text, resolved_pins

REPORT = {
    "install": [
        {"metadata": {"name": "Playwright", "version": "1.55.0"}, "requested": True},
        {"metadata": {"name": "greenlet", "version": "3.2.4"}, "requested": False},
    ]
}


def test_the_declared_dependencies_come_from_pyproject() -> None:
    pyproject = {"project": {"name": "hunter", "dependencies": ["playwright>=1.50", "httpx"]}}
    assert declared(pyproject) == ["playwright>=1.50", "httpx"]
    assert declared({"project": {"name": "hunter"}}) == []


def test_pins_come_from_pips_resolution_sorted_by_name() -> None:
    assert resolved_pins(REPORT) == [Pin("greenlet", "3.2.4"), Pin("playwright", "1.55.0")]


def test_the_lock_lists_every_pin_with_every_hash() -> None:
    text = lock_text({Pin("greenlet", "3.2.4"): ["bb", "aa"], Pin("playwright", "1.55.0"): ["cc"]})
    assert text.startswith("# ")
    body = [line for line in text.splitlines() if not line.startswith("#")]
    assert body == [
        "greenlet==3.2.4 \\",
        "    --hash=sha256:aa \\",
        "    --hash=sha256:bb",
        "playwright==1.55.0 \\",
        "    --hash=sha256:cc",
    ]


def test_a_pin_without_published_hashes_cannot_be_locked() -> None:
    with pytest.raises(ValueError, match="playwright==1.55.0 has no published files"):
        lock_text({Pin("playwright", "1.55.0"): []})
