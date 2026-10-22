# Puts a new doctrine project on GitHub the way doctrine needs it. Run by Omar, once, in the
# project's folder after `doctrine init`, with gh logged in as the owner. (Claude's gh calls on
# repository settings are refused on purpose, so this is the one step that is Omar's.)
#
#     powershell -ExecutionPolicy Bypass -File "D:\1 Software\Small tools\Doctrine\policy\new-project-github.ps1" -Name hunter
#
# It commits the template if nothing is committed yet, creates the public repository and pushes
# main, allows squash merges only, adds the bot as a writer and accepts its invitation with the
# bot's token from the admin settings, and protects main. Running it again changes nothing.
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Owner = "OmarAbdo",
    [string]$Bot = "OmarAbdosBot",
    [string]$Settings = "C:\Program Files\ClaudeCode\managed-settings.json"
)
$ErrorActionPreference = "Stop"
$Repository = "$Owner/$Name"

function Invoke-Program([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program $($Arguments -join ' ') failed (exit code $LASTEXITCODE)." }
}

function Invoke-Git([string[]]$Arguments) {
    Invoke-Program "git" (@("-c", "core.fsmonitor=false") + $Arguments)
}

function Publish-Main {
    & git -c core.fsmonitor=false rev-parse --verify -q HEAD | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Invoke-Git @("add", "-A")
        Invoke-Git @("commit", "-q", "-m", "Start from the doctrine template")
    }
    & gh repo view $Repository --json name | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Invoke-Program "gh" @("repo", "create", $Repository, "--public", "--source", ".", "--remote", "origin", "--push")
        return
    }
    Invoke-Git @("push", "-u", "origin", "main")
}

function Set-MergeSettings {
    Invoke-Program "gh" @("api", "-X", "PATCH", "repos/$Repository", "-F", "allow_squash_merge=true",
        "-F", "allow_merge_commit=false", "-F", "allow_rebase_merge=false", "-F", "delete_branch_on_merge=true")
}

function Add-Bot {
    Invoke-Program "gh" @("api", "-X", "PUT", "repos/$Repository/collaborators/$Bot", "-f", "permission=push")
    $owner = $env:GH_TOKEN
    try {
        $env:GH_TOKEN = (Get-Content $Settings -Raw | ConvertFrom-Json).env.GH_TOKEN
        $query = ".[] | select(.repository.full_name == `"$Repository`") | .id"
        $invitations = & gh api user/repository_invitations --jq $query
        foreach ($invitation in @($invitations | Where-Object { $_ })) {
            Invoke-Program "gh" @("api", "-X", "PATCH", "user/repository_invitations/$invitation")
        }
    } finally {
        $env:GH_TOKEN = $owner
    }
}

function Protect-Main {
    $protection = @'
{
  "required_status_checks": { "strict": false, "contexts": ["gates / gates"] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "dismiss_stale_reviews": true, "required_approving_review_count": 1 },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
'@
    $file = Join-Path $env:TEMP "doctrine-protection-$Name.json"
    Set-Content -Path $file -Value $protection -Encoding ascii
    try {
        Invoke-Program "gh" @("api", "-X", "PUT", "repos/$Repository/branches/main/protection", "--input", $file)
    } finally {
        Remove-Item $file -Force
    }
}

Publish-Main
Set-MergeSettings
Add-Bot
Protect-Main
Write-Output "https://github.com/$Repository is public, main is protected (gates / gates, your approval), $Bot can push item branches."
