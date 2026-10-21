# Installs doctrine for every Claude Code session on this PC. Run once, as administrator, from the
# doctrine repository:   powershell -ExecutionPolicy Bypass -File policy\install.ps1
#
# What it does:
#   1. Finds a Python 3.12+ that only administrators can change (or installs Python 3.13 for all
#      users from python.org, checking the file's hash and signature), so no session can alter
#      the interpreter the hooks run on.
#   2. Doctrine and its pinned tools in C:\Program Files\Doctrine (admin-owned, read-only for you).
#   3. C:\Program Files\ClaudeCode\managed-settings.json: doctrine's hooks, which no user or
#      project setting can switch off, and C:\Program Files\ClaudeCode\CLAUDE.md.
#   4. C:\Program Files\Doctrine\venv\Scripts on the machine PATH, so `doctrine` works everywhere.
#   5. With -BotToken (or the token a previous install stored): every Claude Code session works on
#      GitHub as OmarAbdosBot, which can't approve its own pull requests or change protection.
param([string]$BotToken = "")
$ErrorActionPreference = "Stop"

$bot_login = "OmarAbdosBot"
$bot_email = "345973053+OmarAbdosBot@users.noreply.github.com"

$installer_version = "3.13.17"
$installer_sha256 = "5da012101ba2e17113a9a1cd901e9ce1441086f2b7ecb5de06ec94163899a190"
$home_dir = "C:\Program Files\Doctrine"
$claude_dir = "C:\Program Files\ClaudeCode"
$source = Split-Path -Parent $PSScriptRoot

function Invoke-Native([string]$step, [scriptblock]$command) {
    # Windows PowerShell 5.1 turns anything a program writes to stderr (pip's notices) into a
    # terminating error under "Stop"; a program step fails only on its exit code.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $command 2>&1 | ForEach-Object { "$_" } } finally { $ErrorActionPreference = $previous }
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit code $LASTEXITCODE)" }
}

function Test-AdminOwned([string]$folder) {
    # True when no ordinary account may write to the folder.
    $writers = "Users|Authenticated Users|Everyone|INTERACTIVE|$([Environment]::UserName)"
    $rights = "Write|Modify|FullControl|CreateFiles|AppendData"
    foreach ($rule in (Get-Acl $folder).Access) {
        $ordinary = $rule.IdentityReference.Value -match "\\($writers)$" -or $rule.IdentityReference.Value -match "^($writers)$"
        if ($rule.AccessControlType -eq "Allow" -and $ordinary -and $rule.FileSystemRights.ToString() -match $rights) {
            return $false
        }
    }
    return $true
}

function Find-AdminPython {
    $candidates = @(Get-ChildItem "C:\Program Files\Python3*\python.exe", "C:\Python3*\python.exe" -ErrorAction SilentlyContinue)
    foreach ($python in $candidates | Sort-Object FullName -Descending) {
        $version = & $python.FullName -c "import sys; print(sys.version_info >= (3, 12))"
        if ($version -eq "True" -and (Test-AdminOwned $python.DirectoryName)) { return $python.FullName }
    }
    return $null
}

function Install-Python {
    $file = Join-Path $env:TEMP "python-$installer_version-amd64.exe"
    $address = "https://www.python.org/ftp/python/$installer_version/python-$installer_version-amd64.exe"
    Invoke-WebRequest -Uri $address -OutFile $file -UseBasicParsing
    if ((Get-FileHash $file -Algorithm SHA256).Hash -ne $installer_sha256) { throw "The Python installer's hash is wrong." }
    $signature = Get-AuthenticodeSignature $file
    if ($signature.Status -ne "Valid" -or $signature.SignerCertificate.Subject -notmatch "Python Software Foundation") {
        throw "The Python installer isn't signed by the Python Software Foundation."
    }
    $target = "C:\Program Files\Python313"
    $process = Start-Process $file -Wait -PassThru -ArgumentList "/quiet", "InstallAllUsers=1", "TargetDir=`"$target`"", "PrependPath=0", "Include_test=0", "Include_launcher=0", "Shortcuts=0"
    if ($process.ExitCode -ne 0) { throw "The Python installer failed (exit code $($process.ExitCode))." }
    return "$target\python.exe"
}

function Get-BotEnvironment([string]$token) {
    # Claude's gh and git act as the bot: GH_TOKEN for gh, gh as git's only GitHub credential
    # helper, and the bot as author and committer. Omar's own terminals keep his account.
    if (-not $token) { return "{}" }
    $environment = [ordered]@{
        GH_TOKEN = $token
        GIT_AUTHOR_NAME = $bot_login; GIT_AUTHOR_EMAIL = $bot_email
        GIT_COMMITTER_NAME = $bot_login; GIT_COMMITTER_EMAIL = $bot_email
        GIT_CONFIG_COUNT = "2"
        GIT_CONFIG_KEY_0 = "credential.https://github.com.helper"; GIT_CONFIG_VALUE_0 = ""
        GIT_CONFIG_KEY_1 = "credential.https://github.com.helper"; GIT_CONFIG_VALUE_1 = "!gh auth git-credential"
    }
    return ($environment | ConvertTo-Json -Compress)
}

function Get-StoredToken([string]$settings) {
    if (-not (Test-Path $settings)) { return "" }
    $stored = (Get-Content -Raw $settings | ConvertFrom-Json).env
    if ($stored -and $stored.GH_TOKEN) { return $stored.GH_TOKEN }
    return ""
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as administrator."
}

$python = Find-AdminPython
if (-not $python) { $python = Install-Python }
Write-Output "Python for the hooks: $python"

if (Test-Path $home_dir) { Remove-Item -Recurse -Force $home_dir }
New-Item -ItemType Directory -Force "$home_dir\current" | Out-Null
foreach ($part in "src", "rules", "templates", "samples", "policy", "requirements", "pyproject.toml") {
    Copy-Item -Recurse (Join-Path $source $part) "$home_dir\current\$part"
}

$venv_python = "$home_dir\venv\Scripts\python.exe"
$pip = "--disable-pip-version-check", "--no-input", "--quiet"
Invoke-Native "Creating the virtual environment" { & $python -m venv "$home_dir\venv" }
Invoke-Native "Installing the pinned tools" {
    & $venv_python -m pip install @pip --require-hashes -r "$home_dir\current\requirements\tools.txt"
}
Invoke-Native "Installing doctrine" { & $venv_python -m pip install @pip --no-deps -e "$home_dir\current" }
Invoke-Native "Doctrine's self-test" { & $venv_python -I -m doctrine selftest }

New-Item -ItemType Directory -Force $claude_dir | Out-Null
$settings = Join-Path $claude_dir "managed-settings.json"
if ((Test-Path $settings) -and -not (Test-Path "$settings.before-doctrine")) {
    Copy-Item $settings "$settings.before-doctrine"
}
if (-not $BotToken) { $BotToken = Get-StoredToken $settings }
$template = Get-Content -Raw "$home_dir\current\policy\managed-settings.template.json"
$filled = $template.Replace("{{python}}", $venv_python.Replace("\", "/"))
$filled = $filled.Replace('"env": {}', '"env": ' + (Get-BotEnvironment $BotToken))
$null = $filled | ConvertFrom-Json
[IO.File]::WriteAllText($settings, $filled)
Write-Output ("GitHub identity for Claude: " + $(if ($BotToken) { $bot_login } else { "Omar's own (no bot token)" }))
Copy-Item "$home_dir\current\policy\CLAUDE.md" (Join-Path $claude_dir "CLAUDE.md") -Force

$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($path -notlike "*$home_dir\venv\Scripts*") {
    [Environment]::SetEnvironmentVariable("Path", "$path;$home_dir\venv\Scripts", "Machine")
}

foreach ($folder in $home_dir, $claude_dir, (Split-Path $python)) {
    if (-not (Test-AdminOwned $folder)) { throw "$folder can be changed by ordinary accounts; doctrine isn't safe there." }
}
Write-Output "Doctrine installed: only administrators can change it. Restart VS Code and Claude Code."
