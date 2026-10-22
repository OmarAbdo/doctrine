# Doctrine's own repository

You are changing doctrine itself, under doctrine. The admin CLAUDE.md and the hooks already apply.
This file is only a map: read what the task needs, nothing more.

- Start with [README.md](README.md). Its table says which doc answers which question.
- Code layout: [docs/code-map.md](docs/code-map.md). The rule table: [rules/rules.toml](rules/rules.toml).
- Why something is the way it is: [docs/decisions.md](docs/decisions.md). Change a decision only
  with Omar, and record the new one there.
- Each item's tests go in their own test file: parallel items appending to one file conflicted.
- Keep pull requests small (400 changed lines, 15 files); split work into items that each merge.
- `.venv-dev/Scripts/doctrine.exe` runs this working tree; plain `doctrine` runs the installed
  release. Use the first one to test a change to doctrine's own commands (for example `selftest`).
- Every git call doctrine makes passes `-c core.fsmonitor=false`. Keep it that way (see
  docs/history.md, "fsmonitor").
