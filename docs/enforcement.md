# Enforcement: what is enforced, where, and what a refusal means

Doctrine enforces its rules in four places. Each one catches what the one before it can't, so no
single gap lets a change through.

| Where | When it runs | What it judges | Who can loosen it |
|---|---|---|---|
| Claude Code hooks (admin settings) | On every tool call and turn of every session on the PC | The session's actions | Nobody without admin rights; Claude never runs elevated |
| The git `pre-commit` hook | On every commit | `doctrine check` on the working tree | Nobody: `--no-verify` and `core.hooksPath` are refused |
| CI (`self.yml` for doctrine, `project-gates.yml` for projects) | On every pull request | The committed result | Nobody: it runs on GitHub |
| Branch protection and `merge.yml` | On merge | Gates passed and Omar approved this exact commit | Omar only |

## 1. Claude Code hooks

**Where:** `C:\Program Files\ClaudeCode\managed-settings.json` (admin-owned,
`allowManagedHooksOnly`) runs `python -I -m doctrine hook <event>` from the current release.
**Code:** `src/doctrine/adapters/claude/` and `src/doctrine/application/guard.py`.

| Event | What it does |
|---|---|
| SessionStart | Tells Claude the project, branch, outcome metric, line state, active item and the two core rules |
| PreToolUse on Bash/PowerShell | Judges each command of the line on its own (split on `;`, `&&`, `\|\|`, `\|` and newlines) against the command policy below |
| PreToolUse on Edit/Write/MultiEdit/NotebookEdit | Refuses edits to protected files, to `work/` and `metrics/`, without an active item, outside the item's scope, to source code before the red run of a feature/fix/restore, and to anything but restore items while the line is stopped |
| PostToolUse on file edits | Formats the file, lints it with the project's rules, and runs doctrine's own source rules on service code; problems go back to Claude at once |
| Stop | Sends Claude back to work when its final message claims success over changes that no `doctrine check` has passed since (three times at most; then the turn may end and the override is recorded) |

### The command policy (`domain/safety/command_policy.py`)

| Rule | Refuses | Do instead |
|---|---|---|
| skip-hooks | `--no-verify`, `-n` on commit, hook-skipping env | Fix what the hooks report |
| hooks-path | Changing `core.hooksPath` | Same |
| force-push | `push --force`, `-f`, `+ref` | `--force-with-lease` on your item branch |
| github-admin | `gh pr merge`, repository edits, secrets, and `gh api` calls on branch protection, rulesets, collaborators, Actions permissions, webhooks or keys (reads included) | Open a pull request; settings are Omar's |
| credentials | `gh auth token/login/switch`, `git credential`, Windows credential store | Work with the account you were given |
| elevation | `runas`, `sudo`, `-Verb RunAs` | Ask Omar |
| doctrine-override | Any `DOCTRINE_*=` variable | Doctrine has no off switch |
| push-main (in a project) | Pushing to main or master | Push the item branch |
| main-branch (in a project) | Committing on main; pushing from main (tags only are fine) | Start an item |
| protected-path | A write (redirect, copy, move, delete, `Set-Content`...) that names a protected path; stream redirections like `2>&1` are not writes | Change it through an approved pull request |
| command-owned (in a project) | A shell write to a work item (`work/<n>-*.toml`) or to `metrics/outcome.jsonl` | `doctrine item scope <patterns>` widens the active item; `doctrine metric record` records the outcome |

### Protected files (`domain/safety/protected.py`)

- **Anywhere:** `C:\Program Files\Doctrine`, `C:\Program Files\ClaudeCode`, `.claude/settings*`.
- **At a project's root:** `.doctrine/` (state and evidence), `.git/hooks`,
  `.github/workflows/doctrine*`, `CODEOWNERS`, and `evals/<task>/results.jsonl` (recorded eval
  runs, written only by `doctrine eval run`).
- **Written by commands only, by file tools and by the shell (#59):** `work/` (`doctrine item`) and `metrics/`
  (`doctrine metric record`).

## 2. The git hook

`doctrine init` installs `.git/hooks/pre-commit`, which runs `doctrine check`. The hooks folder is
protected, and skipping it is refused.

## 3. CI gates

**Where:** doctrine itself runs `.github/workflows/self.yml`. A project's
`.github/workflows/doctrine.yml` calls doctrine's reusable `project-gates.yml`, pinned to a release
tag. **Code:** `src/doctrine/adapters/cli/gates/`.

| Gate | Command | Passes when |
|---|---|---|
| Every rule | `doctrine check` | Every tool and rule passes on every service |
| Scope and size | `doctrine ci scope` | The branch is an item, every changed file is in its scope, and it changes ≤ 400 lines and ≤ 15 files (line endings don't count) |
| Red first | `doctrine ci red-first` | Every new test fails on the base branch's code (feature, fix and restore items) |
| Coverage | `doctrine ci coverage` | ≥ 85% of the changed lines run under the tests |
| Mutation | `doctrine ci mutation` | ≥ 70% of up to 30 mutants of the changed domain and application lines are caught by the unit tests |
| Description | `doctrine ci description` | The pull request has What changed, Why, Proof and Not verified, each filled in |
| Evals | `doctrine ci evals` | Every changed prompt or eval set has a recorded run on its new version at or over the minimum; a drop on the same eval set waits for the approver |
| Goalposts | `doctrine ci goalposts` | Nothing was loosened, or the approver approved this commit |

**Goalposts (what needs Omar's approval):**
- a looser limit, or a limit removed;
- a new exception, such as an allowed suppression;
- the outcome's metric or command changed, or its baseline or stop value lowered;
- an AI task removed, its minimum lowered, or a judge turned into a plain task;
- a service's architecture or profile changed;
- an eval case's expected answer changed or removed;
- the doctrine version or the approver changed;
- any change under `.github/`, `rules/`, `policy/` or `CODEOWNERS`.

The approver is read from the base commit, so a pull request can't name its own approver.

## 4. Branch protection and merging

- **Doctrine's main:** a pull request, the `self` check, one approval on the latest commit (stale
  approvals dismissed), admins included, linear history, no force pushes.
- **`merge.yml`** (or the project's `doctrine-merge.yml`) squash-merges an `item/*` pull request
  once its gates passed on that exact commit.
- **`approval.yml`** (`doctrine-approval.yml` in projects) re-runs the failed check when Omar
  approves, so each commit has one check.

## Proof that it holds

- **`doctrine selftest`:** 17 bad-code expectations and 35 bypass attempts (`samples/`), every one
  caught. CI fails if the share drops below 1.
- **A live run on 2026-10-21,** in a real Claude Code session in bypass-permissions mode:
  - `--no-verify`, code without an item, a hand-written work item and a push to main were all
    refused;
  - a final "everything is fixed and verified" over unchecked changes was sent back, and the
    session ran `doctrine check` and reported the failure instead.
- **Doctrine has been built under these rules since #4.** When a refusal was wrong, it was fixed
  through a reviewed item, never bypassed.
