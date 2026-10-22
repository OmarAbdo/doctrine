# The machine: install, update, where things live, and repairs

## Where things live on the PC

| Path | What | Who can change it |
|---|---|---|
| `C:\Program Files\Doctrine\releases\<12-char commit>\` | One installed release: its own venv, the pinned tools and doctrine. The newest 3 stay | Administrators, and the update task (SYSTEM) |
| `C:\Program Files\Doctrine\bin\doctrine.cmd`, `bin\doctrine` | The `doctrine` command for cmd/PowerShell and for Git Bash. Both follow the current release. `bin` is on the machine PATH | Same |
| `C:\Program Files\Doctrine\update.ps1`, `doctrine-release.psm1` | The updater and its module, copied from the current release | Same |
| `C:\Program Files\Doctrine\update.log` | One line per install or failure | Written by the updater |
| `C:\Program Files\Doctrine\last-check.json` | The last update check: time, main's commit, result (`installed`, `up to date` or the failure) | Written by the updater |
| `C:\Program Files\ClaudeCode\managed-settings.json` | Doctrine's hooks for every Claude Code session (`allowManagedHooksOnly`), and the bot's identity in `env` | Administrators |
| `C:\Program Files\ClaudeCode\CLAUDE.md` | The short note every session gets (from `policy/CLAUDE.md`) | Administrators |
| `C:\Python314` (or `C:\Program Files\Python313`) | The admin-owned Python the releases are built from | Administrators |
| Task Scheduler, "Doctrine update" | Runs `update.ps1` as SYSTEM every 30 minutes and at startup | Administrators |

**Note:** `allowManagedHooksOnly` turns off hooks in user settings. That is why Omar's voice
notification (`voice-notify.mjs`) is in the managed settings' Stop hooks, in
`policy/managed-settings.template.json`.

## Install (once)

**Who, when:** Omar, as administrator, on a new PC or to change the bot's token.

```
powershell -ExecutionPolicy Bypass -File policy\install.ps1 -BotToken <OmarAbdosBot classic token>
```

Run it from a clone of this repository. It:

1. Finds a Python 3.12+ that only administrators can change. Without one, it downloads Python
   3.13.17 from python.org, checks its sha256 and its Python Software Foundation signature, and
   installs it for all users.
2. Builds a release from the clone's commit: a venv, the tools from `requirements/tools.txt` with
   `--require-hashes`, and doctrine itself. It runs the self-test and stops unless everything is
   caught.
3. Copies the updater, the shims and CLAUDE.md. It writes `managed-settings.json` last, so a
   failed install never leaves half-switched hooks.
4. Puts `bin` on the machine PATH and registers the update task.
5. Refuses to finish if an ordinary account could change any of these folders.

Then restart VS Code and Claude Code.

## Update (automatic)

**What:** every 30 minutes, the task asks GitHub for main's head commit. If it isn't installed, the
task downloads that commit as an archive and builds a new release folder. The release must pass its
self-test; then it installs itself with its own module, and the hooks switch over. Old releases
beyond 3 are removed.
**Why it's safe:** main only changes through pull requests Omar approved.
**A running session** keeps the release it started with. New sessions get the new one.
**How to see it worked:** the last line of `update.log`, or `last-check.json`.

## The bot's identity

**What:** `managed-settings.json` `env` holds `GH_TOKEN` (the bot's token), a git credential helper
(`!gh auth git-credential`) and the bot as git author and committer
(`OmarAbdosBot <345973053+OmarAbdosBot@users.noreply.github.com>`). Every `git push` and `gh`
call in a session acts as the bot.
**Never** print, copy or commit the token. Reading credentials is refused by the `credentials`
rule.
**To change the token:** create a new classic token on the bot account (scope `repo`), then run
the installer again with `-BotToken`.

## Repairs

| Symptom | Cause | Fix |
|---|---|---|
| `update.log` shows a failure and the release doesn't change | The new release failed its build or self-test | Read the line. If main is broken, fix it through a pull request; the current release stays in place meanwhile |
| `last-check.json` is old | The task isn't running | Task Scheduler: check "Doctrine update" is enabled. Its last result should be 0 |
| `'C:\Program' is not recognized` in Git Bash | An old shim | Fixed in #13. Run the installer again if `bin\doctrine` is missing |
| PC slow, hundreds of `git.exe fsmonitor--daemon` processes | Git's fsmonitor (Git for Windows turns it on system-wide) | `git config --global core.fsmonitor false`, then end the daemons. Doctrine's own calls already turn it off |
| Hooks seem not to run | VS Code or Claude Code started before the install | Restart them. `doctrine` on the PATH needs a new terminal |
| A refusal that looks wrong | A bug in doctrine | Tell Omar, then fix it through an item in this repository. Never work around it |
| GitHub calls fail with 401 | The bot's token expired or was revoked | New token, then the installer with `-BotToken` |
