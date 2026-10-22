# History: why doctrine exists and how it was built

## Who

- **Omar** (GitHub `OmarAbdo`): owner and the only approver. His approval of a pull request is the
  only thing that loosens a rule, merges a change or overrides a gate. Never a message in a chat.
- **OmarAbdosBot**: the bot GitHub account. Every commit, push and pull request Claude makes is
  done as the bot. GitHub doesn't let you approve your own pull request, so Claude's work needs a
  separate author for Omar's approval to count. It has write access to Omar's repositories and
  nothing more.
- **Claude Code**: builds doctrine and every project under doctrine's hooks.

## Why: what went wrong in HQ

HQ was an end-to-end, mostly autonomous job-application pipeline. In two days it got 95 commits,
and the number of applications sent per day fell from 18 to 0. What happened:

- **No evals.** Prompts grew one incident at a time ("whack-a-mole"): every fix for one bad output
  was a new instruction, and nothing measured whether a change helped or hurt. This is the failure
  Hamel Husain describes in "Your AI product needs evals" (hamel.dev/blog/posts/evals).
- **No outcome in sight.** Commits measured activity. Nobody watched the one number the project
  existed for.
- **Unreadable code.** One folder for everything, long files, one-letter names, nested loops and
  branching. Nobody, Claude included, could see what a change would break.
- **Written rules didn't hold.** HQ had a CLAUDE.md, invariants, decision records and 394 tests.
  They were advice, and under pressure advice loses.

On 2026-10-21 Omar judged HQ unfixable and asked for "an iron framework from hell that Claude Code
will never leak from". It would be the base for every future project, so that this never happens
again.

The principle that came out of it: **rules are enforced by machinery** (hooks, git hooks, CI,
branch protection, admin-owned files). Instructions only explain where things are.

## When: how it was built

All times are Omar's local time (UTC+2). Pull request numbers link to github.com/OmarAbdo/doctrine.

**2026-10-21: the core.**
- Rule table, Python profile, command line, Claude Code hooks, CI gates, self-test, admin
  installer, pinned and hashed tools.
- Omar tightened the limits to complexity 7 and nesting 2.
- The installer stopped needing winget, which isn't on Windows 10 Home.
- The repository went public: on GitHub Free, only public repositories get branch protection.
- The bot account was created and given access.
- #4 put the bot, auto-merge, unique item numbers and approval re-runs in place.
- #5: commands are judged one by one, so one bad command no longer refuses the whole line.
- #6: doctrine updates itself from the approved main.

**2026-10-22: hardening and the rest of the scope.**
- #7, #8 and #17 fixed refusals that were wrong: `2>&1` was read as a file write; the edit review
  now applies the same rules as `doctrine check`; protected project files are protected at a
  project's root only.
- #13: `doctrine` works from Git Bash with quoted arguments (a bash shim beside the `.cmd`).
- #14: doctrine never starts git's fsmonitor daemon (see the incidents below).
- #15 and #26: an approval re-runs the failed check instead of starting a second run, in doctrine
  and in new projects.
- #16: each release installs itself, and every update check leaves a trace.
- #18: `doctrine item resume` reopens an item after review feedback.
- #19 and #20: small pull requests (400 lines, 15 files) and a four-section description.
- #21 and #24: the command line regrouped into `commands/` and `gates/`.
- The eval kit:
  - #10: AI tasks in the contract;
  - #22: the rule a changed prompt must pass;
  - #25 and #30: `doctrine eval run`;
  - #27: judge alignment;
  - #28: an eval-set crash fixed;
  - #31: the CI gate;
  - #32: recorded runs protected;
  - #33 and #36: the labelling page.
- Mutation testing: #11 (mutants), #23 (running them), #35 (the CI gate).
- #29 and #37: line-ending-only changes stop counting toward an item's size, and every file is
  stored with LF.
- Omar dropped TypeScript from this repository. It becomes its own doctrine later, so that
  everything is finished in Python first.

## Incidents worth remembering

- **fsmonitor (2026-10-22).** Git for Windows' system config turns on `core.fsmonitor`. Every test
  repository then started a background daemon that never exits. 921 of them ran the PC out of
  memory and crashed VS Code, git and Claude. The fix: global `core.fsmonitor false`, and every git
  call doctrine makes passes `-c core.fsmonitor=false` (#14).
- **A stale failed check blocked merges.** A review started a second CI run. The first run, failed
  before the approval, stayed red, and branch protection counted both. Now an approval re-runs the
  failed run (#15, #26).
- **Review events have no branch names.** On `pull_request_review` events GitHub leaves
  `base_ref`/`head_ref` empty. The gates read the event file instead.
- **CI leaked into tests.** `GITHUB_HEAD_REF` and the event file reached tests that build their own
  repositories. An autouse fixture clears them (`tests/integration/conftest.py`).
- **Path too long.** Release folders named by the full commit sha broke `ensurepip`. They use 12
  characters now.
- **PowerShell 5.1** turns a program's stderr into an error. Installer steps go through
  `Invoke-Native` and fail on the exit code only.
- **A merge conflict resolved by hand** left one-space indentation in a test (#20). Parallel items
  had appended to the same test file. Since then, each item's tests go in their own file.
- **An eval-set change would have crashed a gate** (#28). The gate read a field that eval sets
  don't have, and its tests used the same wrong format. Found while building on it.
- **Doctrine refused its own author** many times: a tag push from main, a whole command line judged
  as one command, template files protected as if they were a project's own. Each was fixed through
  an item, never bypassed.
