# Doctrine

The rules every project starts from, enforced by machinery that Claude Code can't loosen. Doctrine
was written after HQ, where a capable assistant shipped 95 commits in two days while the one number
that mattered (applications sent per day) fell from 18 to 0.

**What:** hooks on every Claude Code session, a git hook, CI gates and branch protection. Together
they hold a project to readable code, tests written first, small reviewed pull requests, a measured
outcome and measured AI prompts.
**Why:** written rules (CLAUDE.md, invariants, 394 tests) didn't stop HQ from drifting, so doctrine
enforces its rules in code. CLAUDE.md is only the map.
**Who:** Omar owns it and approves every change. The bot account OmarAbdosBot does all of Claude's
GitHub work. Claude builds under doctrine's own rules.
**Where:** this repository (public, so that main can be protected on GitHub Free), installed on
Omar's PC under `C:\Program Files\Doctrine` and `C:\Program Files\ClaudeCode`.
**When:** built on 2026-10-21 and 2026-10-22; it updates itself from main every 30 minutes.

## Read this first

| You want to | Read |
|---|---|
| Know why doctrine exists and how it came to be | [docs/history.md](docs/history.md) |
| Know why it is built this way, and what was rejected | [docs/decisions.md](docs/decisions.md) |
| See what is enforced, where, and what a refusal means | [docs/enforcement.md](docs/enforcement.md) |
| Work in a doctrine project: items, tests, pull requests | [docs/working-in-a-project.md](docs/working-in-a-project.md) |
| Understand the code rules, test kinds, coverage and mutation testing | [docs/code-quality.md](docs/code-quality.md) |
| Measure an AI prompt or judge: eval sets, runs, labels | [docs/evals.md](docs/evals.md) |
| Start a new project from doctrine | [docs/new-project.md](docs/new-project.md) |
| Install, update or repair doctrine on the PC | [docs/machine.md](docs/machine.md) |
| Change doctrine's own code | [docs/code-map.md](docs/code-map.md) |
| Know what is not built and what is open | [docs/roadmap.md](docs/roadmap.md) |

## How a change goes, in one screen

```
doctrine item start --kind feature --title "Search by city" --scope "src/jobs/search/**"
# write the failing test
doctrine test            # recorded red
# write the code; every edit is formatted and linted on the spot
doctrine test            # green
doctrine check           # every rule
doctrine item done       # only with a red run, a passing check and nothing unchecked
git push -u origin HEAD && gh pr create --title "..." --body-file body.md
```

Claude never merges. The pull request merges itself once every gate has passed on its latest
commit and Omar has approved that commit.

## Proof that it works

- `doctrine check` on doctrine itself: every rule, every tool.
- `doctrine selftest`: every bad sample in [samples/python](samples/python) and every bypass
  attempt in [samples/attacks.toml](samples/attacks.toml) must be caught (52 of 52 on
  2026-10-22). The share caught is doctrine's own outcome metric.
- Doctrine has been built under its own rules since its fourth pull request. It refused its own
  author's shortcuts, and every refusal that turned out wrong was fixed through a reviewed item.
