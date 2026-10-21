# Installs doctrine for every Claude Code session on this PC. Run once, as administrator, from the
# doctrine repository:   powershell -ExecutionPolicy Bypass -File policy\install.ps1
#
# What it does:
#   1. Python 3.13 for all users (C:\Program Files\Python313), so the interpreter is admin-owned.
#   2. Doctrine and its pinned tools in C:\Program Files\Doctrine (admin-owned, read-only for you).
#   3. C:\Program Files\ClaudeCode\managed-settings.json: doctrine's hooks, which no user or
#      project setting can switch off, and C:\Program Files\ClaudeCode\CLAUDE.md.
#   4. C:\Program Files\Doctrine\venv\Scripts on the machine PATH, so `doctrine` works everywhere.
$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as administrator."
}

$source = Split-Path -Parent $PSScriptRoot
$home_dir = "C:\Program Files\Doctrine"
$claude_dir = "C:\Program Files\ClaudeCode"
$python = "C:\Program Files\Python313\python.exe"

if (-not (Test-Path $python)) {
    winget install --exact --id Python.Python.3.13 --scope machine --silent `
        --accept-package-agreements --accept-source-agreements
    if (-not (Test-Path $python)) { throw "Python 3.13 for all users didn't install at $python" }
}

if (Test-Path $home_dir) { Remove-Item -Recurse -Force $home_dir }
New-Item -ItemType Directory -Force "$home_dir\current" | Out-Null
foreach ($part in "src", "rules", "templates", "samples", "policy", "requirements", "pyproject.toml") {
    Copy-Item -Recurse (Join-Path $source $part) "$home_dir\current\$part"
}

& $python -m venv "$home_dir\venv"
$venv_python = "$home_dir\venv\Scripts\python.exe"
& $venv_python -m pip install --quiet --require-hashes -r "$home_dir\current\requirements\tools.txt"
& $venv_python -m pip install --quiet --no-deps -e "$home_dir\current"
& $venv_python -I -m doctrine selftest

New-Item -ItemType Directory -Force $claude_dir | Out-Null
$settings = Join-Path $claude_dir "managed-settings.json"
if (Test-Path $settings) { Copy-Item $settings "$settings.before-doctrine" -Force }
$template = Get-Content -Raw "$home_dir\current\policy\managed-settings.template.json"
$template.Replace("{{python}}", $venv_python.Replace("\", "/")) | Set-Content -Encoding utf8 $settings
Copy-Item "$home_dir\current\policy\CLAUDE.md" (Join-Path $claude_dir "CLAUDE.md") -Force

$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($path -notlike "*$home_dir\venv\Scripts*") {
    [Environment]::SetEnvironmentVariable("Path", "$path;$home_dir\venv\Scripts", "Machine")
}

# Program Files grants users read and execute only; show it so the install can be checked.
icacls $home_dir | Select-Object -First 4
icacls $claude_dir | Select-Object -First 4
Write-Output "Doctrine installed. Restart Claude Code (and VS Code) so every session loads it."
