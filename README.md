# Doctrine

The rules every project starts from, enforced by machinery Claude Code can't loosen. Written after
HQ, where a capable assistant shipped 95 commits in two days while the one number that mattered
(applications sent per day) fell from 18 to 0.

## What it enforces, and where

| Layer | What runs there | Can Claude loosen it? |
|---|---|---|
| Admin settings (`C:\Program Files\ClaudeCode`) | Hooks on every session: refused shortcuts, item scope, failing test first, a formatted and linted file after every edit, no "it works" over unchecked changes, a session brief | No: admin-only files, managed hooks can't be disabled |
| Git | `pre-commit` runs `doctrine check` | Only with `--no-verify`, which the hooks refuse |
| CI (`project-gates.yml`) | Every rule again, the item's scope and size, new tests fail on the code before the change, changed lines tested, goalposts unchanged or approved | No: it judges the committed result |
| The contract (`doctrine.toml`) | Outcome metric, services, a project's stricter limits | Tightening is free; loosening fails CI until the approver approves the pull request |

## The rules

One table, [rules/rules.toml](rules/rules.toml): function length, complexity, nesting, parameters,
file length, folder size, names of real words, line length, public methods, imports per module,
no inheritance from concrete classes, small interfaces, diff coverage, item size; bans on broad
catches, suppression comments, flag arguments, print and network calls without a timeout. Each
language profile turns the table into its tools' settings, so no config file can drift from it.

Python profile: ruff, pylint (what ruff lacks), `mypy --strict`, pytest, plus doctrine's own rules
on names, function length, hexagonal layers (the domain imports only the standard library), folder
size and a test of the right kind for every module (unit for domain and application, integration
for adapters).

## How a change goes

```
doctrine item start --kind feature --title "Search by city" --scope src/jobs/search/**
# write the failing test
doctrine test            # recorded red
# write the code; every edit is formatted and linted on the spot
doctrine test            # green
doctrine check           # every rule
doctrine item done       # only with a red run, a passing check, nothing unchecked
git push -u origin item/1-search-by-city && gh pr create --fill
```

Claude never merges. The pull request merges itself (`merge.yml`) once every gate passed on its
latest commit, and, where the goalposts moved or the branch protection asks for it, once the
approver approved that commit.

`doctrine metric record` runs the project's outcome command. When the value falls under its stop
value, only `restore` items may change code until it recovers.

## Proof that it works

- `doctrine check` on doctrine itself: every rule, every tool.
- `doctrine selftest`: every bad sample in [samples/python](samples/python) and every bypass in
  [samples/attacks.toml](samples/attacks.toml) must be caught; the share caught is doctrine's own
  outcome metric. A new escape is added there first, failing, then closed.
- Live run (2026-10-21) in a real Claude Code session in bypass-permissions mode: `--no-verify`,
  code without an item, a hand-written work item and a push to main were all refused; a final
  "everything is fixed and verified" over unchecked changes was sent back, and the session ran
  `doctrine check` and reported the failure instead.

## Install

As administrator, from this repository: `powershell -ExecutionPolicy Bypass -File policy\install.ps1`.

## Not built yet

The TypeScript profile, mutation testing and the eval kit (traces, labels, judge alignment).
