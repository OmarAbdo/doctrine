from pathlib import Path

import pytest
from support.projects import new_project


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return new_project(tmp_path)
