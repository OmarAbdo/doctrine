# Code map: doctrine's own code

Doctrine is a hexagonal Python service and follows its own rules. `src/doctrine/`:

## domain/ (standard library only)

| Folder | Responsibility |
|---|---|
| `rules/` | The rule table (`table.py`), names made of words (`names.py`), findings |
| `python/` | Python source rules (`source.py`: function length, names, suppressions, imports, interfaces, inheritance, domain purity) and layout rules (`layout.py`: layers, folder size, test kinds) |
| `governance/` | The contract (`contract.py`), work items, the evidence chain and when an item is ready, goalposts (what needs approval), success claims, pull request descriptions |
| `safety/` | The command policy (`command_policy.py`) and protected paths (`protected.py`) |
| `evals/` | AI tasks, eval cases, scoring, judge alignment, labels and traces, recorded results and the evals gate's rule |
| `mutation/` | Mutation operators (`operators.py`) |

## application/ (uses the domain and ports)

| Module | Responsibility |
|---|---|
| `guard.py` | The hooks' decisions: may this tool call run, may this turn end |
| `check.py`, `python_tools.py` | `doctrine check` for a service, and the standard tools configured from the rule table |
| `brief.py` | The session brief |
| `selftest.py` | The self-test over `samples/` |
| `mutation.py` | Running mutants and the mutation score |
| `evals.py` | Running an AI task on its eval set |
| `ports.py` | The interfaces adapters implement |

## adapters/ (the outside world)

| Folder | Responsibility |
|---|---|
| `claude/` | Claude Code hook entry points (`hooks.py`), the edit review, the Stop gate, the session's situation, transcripts |
| `cli/main.py` | The `doctrine` command line: parsers and dispatch |
| `cli/commands/` | Working commands: check and test, init, items and metric, eval run, eval label, selftest |
| `cli/gates/` | The CI gates: scope and goalposts (`ci_commands.py`), red-first, coverage, mutation, description, evals, GitHub reviews |
| `storage/` | Project files and the contract, state, evidence, the metric log, eval files |
| `tools/` | Git, subprocess tools, the mutation trial (a temporary copy of a project), an AI task's command |
| `web/` | The labelling page |

## Around the code

| Path | What |
|---|---|
| `rules/rules.toml` | The rule table |
| `requirements/tools.in`, `tools.txt` | Pinned tools, with every file's sha256 |
| `samples/` | Bad code and bypass attempts the self-test must catch |
| `templates/python-hexagonal/` | What `doctrine init` copies into a new project |
| `policy/` | The installer, the updater and its module, the admin settings template, the admin CLAUDE.md |
| `.github/workflows/` | `self.yml` (doctrine's CI), `project-gates.yml` (projects' gates, reusable), `merge.yml`, `approval.yml` |
| `tests/unit/`, `tests/integration/` | Tests per layer. `tests/support/projects.py` builds real throwaway projects |
| `work/` | Every work item doctrine was built with |
| `metrics/outcome.jsonl` | Doctrine's own outcome (the self-test share) |

## Changing doctrine

Doctrine changes like any project: an item, a failing test first, `doctrine check`, a pull request.
To test a change to doctrine's own commands before it is installed, run the working tree's command:
`.venv-dev/Scripts/doctrine.exe`. Once merged, the update task installs it within 30 minutes.
