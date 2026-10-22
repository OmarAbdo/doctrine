# Working in a doctrine project

This page is for whoever changes a project: Claude, or Omar by hand. Every step below is enforced
(see docs/enforcement.md). The commands are the way through.

## The life of a change

**1. Start an item.**

```
doctrine item start --kind feature --title "Search by city" --scope "src/jobs/search/**" "src/jobs/domain/city.py"
```

- **Kind:**
  - `feature`, `fix`, `restore`: must start with a failing test.
  - `refactor`: changes structure, not behaviour.
  - `chore`: tooling, docs.
  - `restore` is the only kind allowed while the line is stopped.
- **Scope:** the files and folders the item may change, as glob patterns. `tests/**` and `work/**`
  are always in scope. A pattern may not start with `*`: name a folder or a file.
- **What it does:** writes `work/<id>-<title>.toml`, creates and switches to
  `item/<id>-<title>`, and records the item as active in `.doctrine/state.json`. The id is unique
  across all local and remote branches.

**2. Red first** (feature, fix, restore). Write the test, then run `doctrine test` (pass test
paths to run only those). It must fail, and that red run is recorded as evidence. Until then,
edits to source code are refused. Put each item's tests in their own test file: two items
appending to the same file will conflict.

**3. Write the code.** After every edit, the file is formatted and linted, and problems come back
at once. Fix them before moving on.

**4. Check.** `doctrine check` runs every rule and every tool on every service. Don't say anything
works until it has passed. The Stop hook sends unproven claims back.

**5. Finish.** Commit on the item branch, then run `doctrine item done`. It refuses while a
feature or fix has no recorded red run, while the last check didn't pass, or when a test went red
after it. Then push and open a pull request:

```
git push -u origin HEAD
gh pr create --title "<the item's title>" --body-file body.md
```

**6. The pull request.** The body needs four sections, each filled in:

```
## What changed
## Why
## Proof
## Not verified
```

"Proof" is the failing-first test, the check, a real run. "Not verified" says what none of that
proves. Write "Nothing" only when everything ran. CI runs the gates (docs/enforcement.md). When
they pass and Omar approves the commit, it merges itself. Claude never merges.

**7. Review feedback.** `doctrine item resume <id>` switches back to the item's branch and makes it
active again. Change, check and `doctrine item done` again, then push to the same branch.

## Size

An item changes at most 400 lines (added plus removed) and 15 files. A change of line endings only
doesn't count. When the work is bigger, split it into items that each make sense and merge on
their own: first the domain, then the adapter, then the command.

## The outcome metric and the line stop

- **What:** `doctrine.toml` names the project's outcome (`[outcome]`): the metric, the command that
  computes it from real data and prints one number, the baseline, and `stop_below`.
- **How:** `doctrine metric record` runs the command and appends the value to
  `metrics/outcome.jsonl`.
- **When the value falls under `stop_below`:** the line is stopped, and only `restore` items may
  change code until a recorded value recovers. The session brief says so at the start of every
  session.
- **First item of a new project:** agree the metric with Omar and define it.

## Dependencies

- **What:** third-party packages go in `pyproject.toml` `[project] dependencies`, then run
  `doctrine deps lock`. It resolves them with pip and writes `requirements.lock`: every package,
  transitive ones included, at an exact version with the sha256 of every published file. Commit both
  files together.
- **How they're used:** with a lock present, doctrine builds `.venv` from its own pinned tools plus
  the lock (`--require-hashes`) and runs every tool there: check, test, coverage, red-first and
  mutants. The outcome and AI task commands run with that Python when they start with `python`, and
  `src/` is on their import path. The environment is rebuilt by itself when a lock changes; never
  `pip install` into it by hand, because CI builds it from the lock alone.
- **Why hashed:** a project's packages are as much a supply-chain risk as doctrine's own tools.

## AI tasks

A prompt change needs a measured score. See docs/evals.md:

```
doctrine eval run <task>                          # after changing a prompt or eval set
doctrine eval label <judge> --traces traces.jsonl # Omar labels real outputs for a judge
```

## Commands

| Command | What it does |
|---|---|
| `doctrine init --name "..." --approver OmarAbdo` | A new project from the template, with its git hook |
| `doctrine item start / show / done / resume <id>` | The item lifecycle |
| `doctrine test [paths]` | Runs the tests and records the run (red or green) as evidence |
| `doctrine check` | Every rule on every service |
| `doctrine metric record` | Records the outcome metric |
| `doctrine deps lock` | Locks `pyproject.toml`'s dependencies into `requirements.lock` |
| `doctrine eval run <task>` | Runs an AI task on its eval set and records the score |
| `doctrine eval label <judge> --traces <file>` | Opens the labelling page |
| `doctrine selftest` | The share of bad samples and bypasses doctrine catches |
| `doctrine ci <gate> --base <ref>` | The CI gates (scope, red-first, coverage, mutation, description, evals, goalposts) |
| `doctrine hook <event>` | Claude Code's hook entry point (not for people) |

## When doctrine refuses

A refusal says why and what to do instead: do that. If a refusal is wrong, it's a bug in doctrine.
Stop and tell Omar. The fix goes through an item in doctrine's repository, like #7 and #17 did.
Never work around it.
