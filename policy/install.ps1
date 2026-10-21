# Installs doctrine for every Claude Code session on this PC. Run as administrator, from the
# doctrine repository:
#     powershell -ExecutionPolicy Bypass -File policy\install.ps1 [-BotToken <token>]
#
# After this, doctrine keeps itself current: the "Doctrine update" task (SYSTEM, every 30
# minutes and at startup) installs what was merged to its protected main, where every change
# needed Omar's approval, once the new release passes its self-test. Run this script again only
# to change the bot token or if the update log reports a failure it can't get past.
#
# What it sets up:
#   1. A Python 3.12+ that only administrators can change (or Python 3.13 for all users from
#      python.org, checked by hash and signature), so no session can alter the interpreter.
#   2. A release in C:\Program Files\Doctrine\releases\<commit>, proven by its self-test.
#   3. C:\Program Files\ClaudeCode\managed-settings.json (doctrine's hooks, which no user or
#      project setting can switch off; the bot's identity) and CLAUDE.md.
#   4. C:\Program Files\Doctrine\bin on the machine PATH, so `doctrine` works everywhere.
#   5. The update task.
param([string]$BotToken = "")
$ErrorActionPreference = "Stop"

$InstallerVersion = "3.13.17"
$InstallerSha256 = "5da012101ba2e17113a9a1cd901e9ce1441086f2b7ecb5de06ec94163899a190"
$HomeDir = "C:\Program Files\Doctrine"
$ClaudeDir = "C:\Program Files\ClaudeCode"
$Source = Split-Path -Parent $PSScriptRoot
Import-Module (Join-Path $PSScriptRoot "doctrine-release.psm1") -Force

function Find-AdminPython {
    $candidates = @(Get-ChildItem "C:\Program Files\Python3*\python.exe", "C:\Python3*\python.exe" -ErrorAction SilentlyContinue)
    foreach ($python in $candidates | Sort-Object FullName -Descending) {
        $recent = & $python.FullName -c "import sys; print(sys.version_info >= (3, 12))"
        if ($recent -eq "True" -and (Test-AdminOwned $python.DirectoryName)) { return $python.FullName }
    }
    return $null
}

function Install-Python {
    $file = Join-Path $env:TEMP "python-$InstallerVersion-amd64.exe"
    $address = "https://www.python.org/ftp/python/$InstallerVersion/python-$InstallerVersion-amd64.exe"
    Invoke-WebRequest -Uri $address -OutFile $file -UseBasicParsing
    if ((Get-FileHash $file -Algorithm SHA256).Hash -ne $InstallerSha256) { throw "The Python installer's hash is wrong." }
    $signature = Get-AuthenticodeSignature $file
    if ($signature.Status -ne "Valid" -or $signature.SignerCertificate.Subject -notmatch "Python Software Foundation") {
        throw "The Python installer isn't signed by the Python Software Foundation."
    }
    $target = "C:\Program Files\Python313"
    $arguments = "/quiet", "InstallAllUsers=1", "TargetDir=`"$target`"", "PrependPath=0", "Include_test=0", "Include_launcher=0", "Shortcuts=0"
    $process = Start-Process $file -Wait -PassThru -ArgumentList $arguments
    if ($process.ExitCode -ne 0) { throw "The Python installer failed (exit code $($process.ExitCode))." }
    return "$target\python.exe"
}

function Set-MachinePath {
    # The `doctrine` command is the bin\doctrine.cmd shim, which follows the current release.
    $entries = [Environment]::GetEnvironmentVariable("Path", "Machine") -split ";" | Where-Object { $_ }
    $entries = @($entries | Where-Object { $_ -ne "$HomeDir\venv\Scripts" -and $_ -ne "$HomeDir\bin" }) + "$HomeDir\bin"
    [Environment]::SetEnvironmentVariable("Path", ($entries -join ";"), "Machine")
}

function Register-UpdateTask {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$HomeDir\update.ps1`""
    $every = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)
    $triggers = @((New-ScheduledTaskTrigger -AtStartup), $every)
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
    Register-ScheduledTask -TaskName "Doctrine update" -Action $action -Trigger $triggers `
        -Principal $principal -Settings $settings -Force | Out-Null
}

$identity = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as administrator."
}

$python = Find-AdminPython
if (-not $python) { $python = Install-Python }
Write-Output "Python for the hooks: $python"

$commit = (& git -C $Source rev-parse HEAD).Trim()
New-Item -ItemType Directory -Force $HomeDir, $ClaudeDir | Out-Null
Install-Release -Source $Source -Commit $commit -Python $python -HomeDir $HomeDir -ClaudeDir $ClaudeDir -Token $BotToken
Set-MachinePath
Register-UpdateTask

foreach ($folder in $HomeDir, $ClaudeDir, (Split-Path $python)) {
    if (-not (Test-AdminOwned $folder)) { throw "$folder can be changed by ordinary accounts; doctrine isn't safe there." }
}
$identityLine = if (Get-StoredToken (Join-Path $ClaudeDir "managed-settings.json")) { $BotLogin } else { "Omar's own (no bot token)" }
Write-Output "GitHub identity for Claude: $identityLine"
Write-Output "Doctrine $commit installed and keeps itself current. Restart VS Code and Claude Code."
