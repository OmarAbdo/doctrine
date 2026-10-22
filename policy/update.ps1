# Run every 30 minutes and at startup by the "Doctrine update" scheduled task, as SYSTEM.
# Installs what was merged to doctrine's protected main (every change there needed Omar's
# approval) once its self-test passes; until then the current release stays. Log: update.log.
param([string]$ClaudeDir = "C:\Program Files\ClaudeCode")
$ErrorActionPreference = "Stop"
$HomeDir = Split-Path -Parent $PSCommandPath
$Repository = "OmarAbdo/doctrine"
$Log = Join-Path $HomeDir "update.log"
Import-Module (Join-Path $HomeDir "doctrine-release.psm1") -Force

function Write-Log([string]$Text) {
    Add-Content -Path $Log -Value ("{0}Z {1}" -f (Get-Date).ToUniversalTime().ToString("s"), $Text)
}

function Get-MainCommit {
    $headers = @{ "User-Agent" = "doctrine-update"; "Accept" = "application/vnd.github+json" }
    return (Invoke-RestMethod -Uri "https://api.github.com/repos/$Repository/commits/main" -Headers $headers).sha
}

function Get-Source([string]$Commit) {
    $work = Join-Path $env:TEMP "doctrine-$Commit"
    if (Test-Path $work) { Remove-Item -Recurse -Force $work }
    $archive = "$work.zip"
    Invoke-WebRequest -Uri "https://codeload.github.com/$Repository/zip/$Commit" -OutFile $archive -UseBasicParsing
    Expand-Archive -Path $archive -DestinationPath $work -Force
    Remove-Item $archive -Force
    return (Get-ChildItem $work -Directory | Select-Object -First 1).FullName
}

try {
    Update-Doctrine -HomeDir $HomeDir -ClaudeDir $ClaudeDir -MainCommit { Get-MainCommit } -Download { param($Commit) Get-Source $Commit }
} catch {
    Write-Log "update failed, the current release stays: $_"
    Write-LastCheck $HomeDir "" "failed: $_"
    exit 1
}
