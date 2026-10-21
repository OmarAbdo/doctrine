"""The PowerShell that installs and updates doctrine, run for real (PowerShell on Windows, pwsh on
GitHub's Linux runners)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
POLICY = Path(__file__).resolve().parents[2] / "policy"
MODULE = POLICY / "doctrine-release.psm1"
TEMPLATE = POLICY / "managed-settings.template.json"
TIMEOUT_SECONDS = 120

pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="PowerShell isn't installed")


def powershell(script: str) -> str:
    command = f"$ErrorActionPreference = 'Stop'; Import-Module '{MODULE}' -Force; {script}"
    finished = subprocess.run(
        [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    return finished.stdout.strip()


def settings(token: str) -> dict[str, object]:
    script = (
        f"New-SettingsText -Template (Get-Content -Raw '{TEMPLATE}') "
        f"-Python 'C:/Program Files/Doctrine/releases/abc/venv/Scripts/python.exe' -Token '{token}'"
    )
    parsed: dict[str, object] = json.loads(powershell(script))
    return parsed


def test_the_settings_point_every_hook_at_the_release_and_carry_the_bot() -> None:
    filled = settings("ghp_example")
    hooks = json.dumps(filled["hooks"])
    assert hooks.count("releases/abc/venv/Scripts/python.exe") == 4
    assert filled["allowManagedHooksOnly"] is True
    assert filled["env"] == {
        "GH_TOKEN": "ghp_example",
        "GIT_AUTHOR_NAME": "OmarAbdosBot",
        "GIT_AUTHOR_EMAIL": "345973053+OmarAbdosBot@users.noreply.github.com",
        "GIT_COMMITTER_NAME": "OmarAbdosBot",
        "GIT_COMMITTER_EMAIL": "345973053+OmarAbdosBot@users.noreply.github.com",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "credential.https://github.com.helper",
        "GIT_CONFIG_VALUE_0": "",
        "GIT_CONFIG_KEY_1": "credential.https://github.com.helper",
        "GIT_CONFIG_VALUE_1": "!gh auth git-credential",
    }


def test_without_a_token_claude_keeps_the_account_it_has() -> None:
    assert settings("")["env"] == {}


def test_an_update_keeps_the_token_the_last_install_stored(tmp_path: Path) -> None:
    stored = tmp_path / "managed-settings.json"
    stored.write_text(json.dumps({"env": {"GH_TOKEN": "ghp_stored"}}), encoding="utf-8")
    assert powershell(f"Get-StoredToken '{stored}'") == "ghp_stored"
    assert powershell(f"Get-StoredToken '{tmp_path / 'missing.json'}'") == ""


def test_the_doctrine_command_runs_the_current_release_isolated() -> None:
    shim = powershell(
        "Get-ShimText -Python 'C:\\Doctrine\\releases\\abc\\venv\\Scripts\\python.exe'"
    )
    assert '"C:\\Doctrine\\releases\\abc\\venv\\Scripts\\python.exe" -I -m doctrine %*' in shim


def test_old_releases_are_pruned_but_never_the_current_one() -> None:
    script = (
        "ConvertTo-Json -Compress -InputObject @(Select-PrunableReleases "
        "-Releases @('first','second','third','fourth','fifth') -Current 'second' -Keep 3)"
    )
    assert json.loads(powershell(script)) == ["first"]


def test_a_release_goes_live_only_when_its_selftest_caught_everything() -> None:
    assert powershell('Test-SelftestPassed -Output "50 of 50 caught`n1"') == "True"
    assert powershell('Test-SelftestPassed -Output "49 of 50 caught`n0.98"') == "False"
    assert powershell("Test-SelftestPassed -Output ''") == "False"
