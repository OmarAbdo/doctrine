from pathlib import Path

import pytest
from support.projects import new_project


@pytest.fixture(autouse=True)
def outside_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    """The gates read the pull request from GitHub's environment; these tests use their own
    repositories, so a CI run's branch and event must not leak into them."""
    for name in ("GITHUB_HEAD_REF", "GITHUB_EVENT_PATH", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return new_project(tmp_path)
