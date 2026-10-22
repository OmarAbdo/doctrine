"""2026-10-22 (#49): a new project's GitHub setup was a manual list that nothing checked, and the
template still passed a token doctrine stopped needing when it went public."""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "policy" / "new-project-github.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def test_the_script_sets_up_everything_doctrine_needs() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for setting in (
        "--public",
        "collaborators/$Bot",
        "repository_invitations",
        "allow_squash_merge",
        '"gates / gates"',
        '"enforce_admins": true',
        '"dismiss_stale_reviews": true',
        '"required_approving_review_count": 1',
        '"required_linear_history": true',
        '"allow_force_pushes": false',
    ):
        assert setting in text, setting


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell isn't installed")
def test_the_script_parses() -> None:
    check = (
        "$errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{SCRIPT}', [ref]$null, [ref]$errors); if ($errors) {{ $errors; exit 1 }}"
    )
    finished = subprocess.run(
        [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", check],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr


def test_new_projects_pass_no_doctrine_token(project: Path) -> None:
    workflow = (project / ".github" / "workflows" / "doctrine.yml").read_text(encoding="utf-8")
    assert "DOCTRINE_TOKEN" not in workflow
