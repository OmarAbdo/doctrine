# Building and switching doctrine releases, shared by install.ps1 (once, by Omar) and update.ps1
# (the scheduled task). A release is built in its own folder next to the running one, proven by
# its self-test, and only then made current by rewriting the admin settings; a session that is
# running keeps the release it started with.

$BotLogin = "OmarAbdosBot"
$BotEmail = "345973053+OmarAbdosBot@users.noreply.github.com"
$KeepReleases = 3

function Invoke-Native([string]$Step, [scriptblock]$Command) {
    # Windows PowerShell 5.1 turns anything a program writes to stderr (pip's notices) into a
    # terminating error under "Stop"; a program step fails only on its exit code.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Command 2>&1 | ForEach-Object { "$_" } } finally { $ErrorActionPreference = $previous }
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit code $LASTEXITCODE)" }
}

function Get-BotEnvironment([string]$Token) {
    # Claude's gh and git act as the bot: GH_TOKEN for gh, gh as git's only GitHub credential
    # helper, and the bot as author and committer. Omar's own terminals keep his account.
    if (-not $Token) { return "{}" }
    $environment = [ordered]@{
        GH_TOKEN = $Token
        GIT_AUTHOR_NAME = $BotLogin; GIT_AUTHOR_EMAIL = $BotEmail
        GIT_COMMITTER_NAME = $BotLogin; GIT_COMMITTER_EMAIL = $BotEmail
        GIT_CONFIG_COUNT = "2"
        GIT_CONFIG_KEY_0 = "credential.https://github.com.helper"; GIT_CONFIG_VALUE_0 = ""
        GIT_CONFIG_KEY_1 = "credential.https://github.com.helper"; GIT_CONFIG_VALUE_1 = "!gh auth git-credential"
    }
    return ($environment | ConvertTo-Json -Compress)
}

function Get-StoredToken([string]$Settings) {
    if (-not (Test-Path $Settings)) { return "" }
    $stored = (Get-Content -Raw $Settings | ConvertFrom-Json).env
    if ($stored -and $stored.GH_TOKEN) { return $stored.GH_TOKEN }
    return ""
}

function New-SettingsText([string]$Template, [string]$Python, [string]$Token) {
    $filled = $Template.Replace("{{python}}", $Python.Replace("\", "/"))
    $filled = $filled.Replace('"env": {}', '"env": ' + (Get-BotEnvironment $Token))
    $null = $filled | ConvertFrom-Json
    return $filled
}

function Get-ShimText([string]$Python) {
    return "@echo off`r`n`"$Python`" -I -m doctrine %*`r`n"
}

function Get-BashShimText([string]$Python) {
    # Git Bash (Claude Code's shell on Windows) loses quoted arguments through cmd.exe, so it gets
    # its own launcher: a shell script it finds on PATH as plain `doctrine`.
    return "#!/bin/sh`n# The current doctrine release, written by doctrine's installer.`nexec `"$($Python.Replace('\', '/'))`" -I -m doctrine `"`$@`"`n"
}

function Select-PrunableReleases([string[]]$Releases, [string]$Current, [int]$Keep = $KeepReleases) {
    # Releases oldest first. The newest $Keep stay, and the current one always stays.
    $old = @($Releases | Select-Object -First ([Math]::Max(0, $Releases.Count - $Keep)))
    return @($old | Where-Object { $_ -ne $Current })
}

function Get-ReleaseName([string]$Commit) {
    # Short, because pip's deepest files must stay under Windows' 260-character path limit.
    return $Commit.Substring(0, [Math]::Min(12, $Commit.Length))
}

function Test-SelftestPassed([string]$Output) {
    $lines = @($Output -split "`r?`n" | Where-Object { $_.Trim() })
    return ($lines.Count -gt 0 -and $lines[-1].Trim() -eq "1")
}

function Test-AdminOwned([string]$Folder) {
    # True when no ordinary account may write to the folder.
    $writers = "Users|Authenticated Users|Everyone|INTERACTIVE|$([Environment]::UserName)"
    $rights = "Write|Modify|FullControl|CreateFiles|AppendData"
    foreach ($rule in (Get-Acl $Folder).Access) {
        $identity = $rule.IdentityReference.Value
        $ordinary = $identity -match "\\($writers)$" -or $identity -match "^($writers)$"
        if ($rule.AccessControlType -eq "Allow" -and $ordinary -and $rule.FileSystemRights.ToString() -match $rights) {
            return $false
        }
    }
    return $true
}

function Write-Atomically([string]$Path, [string]$Text) {
    $staged = "$Path.new"
    [IO.File]::WriteAllText($staged, $Text)
    Move-Item -Force $staged $Path
}

function Install-Release {
    # Builds the release from $Source under $HomeDir\releases\<short commit>, proves it with its
    # self-test and makes it current. Throws, leaving the current release untouched, when any
    # step fails.
    param([string]$Source, [string]$Commit, [string]$Python, [string]$HomeDir, [string]$ClaudeDir,
          [string]$Token = "")
    $release = Join-Path $HomeDir ("releases\" + (Get-ReleaseName $Commit))
    if (Test-Path $release) { Remove-Item -Recurse -Force $release }
    New-Item -ItemType Directory -Force "$release\source" | Out-Null
    foreach ($part in "src", "rules", "templates", "samples", "policy", "requirements", "pyproject.toml") {
        Copy-Item -Recurse (Join-Path $Source $part) "$release\source\$part"
    }
    $venvPython = "$release\venv\Scripts\python.exe"
    $pip = "--disable-pip-version-check", "--no-input", "--quiet"
    Invoke-Native "Creating the virtual environment" { & $Python -m venv "$release\venv" }
    Invoke-Native "Installing the pinned tools" {
        & $venvPython -m pip install @pip --require-hashes -r "$release\source\requirements\tools.txt"
    }
    Invoke-Native "Installing doctrine" { & $venvPython -m pip install @pip --no-deps -e "$release\source" }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { $selftest = (& $venvPython -I -m doctrine selftest 2>&1 | Out-String) } finally { $ErrorActionPreference = $previous }
    if (-not (Test-SelftestPassed $selftest)) { throw "The self-test of $Commit didn't catch everything:`n$selftest" }
    Set-CurrentRelease -Release $release -Commit $Commit -Python $Python -HomeDir $HomeDir `
        -ClaudeDir $ClaudeDir -Token $Token
}

function Set-CurrentRelease {
    # The admin settings, CLAUDE.md, the `doctrine` command and the updater point at $Release.
    # A token given here replaces the stored one; without one, the stored token stays.
    param([string]$Release, [string]$Commit, [string]$Python, [string]$HomeDir, [string]$ClaudeDir,
          [string]$Token = "")
    $venvPython = "$Release\venv\Scripts\python.exe"
    $settings = Join-Path $ClaudeDir "managed-settings.json"
    if ((Test-Path $settings) -and -not (Test-Path "$settings.before-doctrine")) {
        Copy-Item $settings "$settings.before-doctrine"
    }
    $template = Get-Content -Raw "$Release\source\policy\managed-settings.template.json"
    if (-not $Token) { $Token = Get-StoredToken $settings }
    $text = New-SettingsText -Template $template -Python $venvPython -Token $Token
    # Everything that can fail comes first; the admin settings switch sessions over last.
    Copy-Item "$Release\source\policy\update.ps1", "$Release\source\policy\doctrine-release.psm1" $HomeDir -Force
    Copy-Item "$Release\source\policy\CLAUDE.md" (Join-Path $ClaudeDir "CLAUDE.md") -Force
    New-Item -ItemType Directory -Force "$HomeDir\bin" | Out-Null
    Write-Atomically "$HomeDir\bin\doctrine.cmd" (Get-ShimText $venvPython)
    Write-Atomically "$HomeDir\bin\doctrine" (Get-BashShimText $venvPython)
    Write-Atomically $settings $text
    $at = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    $installed = [ordered]@{ commit = $Commit; release = $Release; python = $Python; at = $at }
    Write-Atomically "$HomeDir\installed.json" ($installed | ConvertTo-Json)
    Remove-OldReleases -HomeDir $HomeDir -Current (Get-ReleaseName $Commit)
}

function Remove-OldReleases([string]$HomeDir, [string]$Current) {
    $releases = @(Get-ChildItem "$HomeDir\releases" -Directory | Sort-Object CreationTime | ForEach-Object Name)
    foreach ($name in (Select-PrunableReleases -Releases $releases -Current $Current)) {
        Remove-Item -Recurse -Force "$HomeDir\releases\$name" -ErrorAction SilentlyContinue
    }
}

function Write-LastCheck([string]$HomeDir, [string]$Main, [string]$Result) {
    # One small file overwritten on every check, so a quiet day still shows the task is alive.
    $check = [ordered]@{ at = (Get-Date).ToUniversalTime().ToString("s") + "Z"; main = $Main; result = $Result }
    Write-Atomically (Join-Path $HomeDir "last-check.json") ($check | ConvertTo-Json)
}

function Update-Doctrine {
    # One check: install main's commit when it is new. The new release installs itself with its
    # own installer code (approved with it on main), so an installer change counts at once.
    param([string]$HomeDir, [string]$ClaudeDir, [scriptblock]$MainCommit, [scriptblock]$Download)
    $installed = Get-Content -Raw (Join-Path $HomeDir "installed.json") | ConvertFrom-Json
    $head = & $MainCommit
    if ($head -eq $installed.commit) {
        Write-LastCheck $HomeDir $head "up to date"
        return
    }
    $source = & $Download $head
    try {
        Import-Module (Join-Path $source "policy\doctrine-release.psm1") -Force -Prefix New
        Install-NewRelease -Source $source -Commit $head -Python $installed.python -HomeDir $HomeDir -ClaudeDir $ClaudeDir
    } finally {
        Remove-Item -Recurse -Force (Split-Path -Parent $source) -ErrorAction SilentlyContinue
    }
    $line = "{0}Z installed {1} (was {2})" -f (Get-Date).ToUniversalTime().ToString("s"), $head, $installed.commit
    Add-Content -Path (Join-Path $HomeDir "update.log") -Value $line
    Write-LastCheck $HomeDir $head "installed"
}

Export-ModuleMember -Function * -Variable BotLogin, BotEmail
