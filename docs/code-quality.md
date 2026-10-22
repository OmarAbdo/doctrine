# Code quality: the rules, the tests, coverage and mutation testing

## Why

HQ's code was unreadable: one folder, long files, one-letter names, nested loops and branching.
Its 394 tests mostly ran code without checking what it did. Doctrine holds code to limits a person
can read in one sitting, and holds tests to proving behaviour.

## What: the rule table

[rules/rules.toml](../rules/rules.toml) is the single source of truth, shared by every language.

| Limit | Value | What it means |
|---|---|---|
| function_lines | ≤ 40 | Lines of one function, signature included |
| complexity | ≤ 7 | Cyclomatic complexity of one function |
| nesting | ≤ 2 | Nested blocks inside one function |
| parameters | ≤ 4 | Parameters, `self`/`cls` not counted |
| file_lines | ≤ 300 | Lines of one source file |
| modules_per_folder | ≤ 10 | Source files directly in one folder: group by responsibility |
| name_length | ≥ 3 | Characters in a name (except `i`, `j`, `_`, `id`, `db`, `io`, `ok`, `ui`, `os`, `x`, `y`) |
| line_length | ≤ 100 | Characters in one line |
| public_methods | ≤ 7 | Public methods of one class |
| imports_per_module | ≤ 12 | Import statements of one module |
| inheritance_depth | ≤ 1 | Bases written in the project: composition first |
| interface_methods | ≤ 5 | Methods of one port or interface |
| diff_coverage | ≥ 85 | Percent of changed lines the tests run |
| mutation_score | ≥ 70 | Percent of mutants in changed code the tests catch |
| item_lines | ≤ 400 | Lines one work item changes, added plus removed |
| item_files | ≤ 15 | Files one work item changes |

**Bans:** catching every exception, comments that silence a linter or type checker (`noqa`,
`type: ignore`, `pylint: disable`), boolean flag parameters, `print`, network calls without a
timeout. **Names:** words, not abbreviations. `cfg`, `msg`, `tmp`, `val`, `res` and 24 more are
banned.

**Who may change it:** a project may tighten any limit in its `doctrine.toml` `[limits]` for free.
Loosening one, in a project or in this table, waits for Omar's approval.

## How: the Python profile

`doctrine check` runs, per service in `doctrine.toml`:

- **ruff:** pycodestyle, pyflakes, bugbear, mccabe, naming, pyupgrade, simplify, returns, perflint,
  pylint rules, unused arguments, commented-out code, blanket `noqa`. Its limits come from the
  table.
- **pylint:** for what ruff lacks, with the same limits.
- **`mypy --strict`.**
- **pytest.**
- **doctrine's own source rules** (`src/doctrine/domain/python/`): function length in lines, names
  made of words, suppression comments, imports per module, interface size, inheritance depth, and
  the layout rules below.

Tool versions are pinned with every file's sha256 (`requirements/tools.txt`, installed with
`--require-hashes`).

## Where code goes: hexagonal layers

A service (`architecture = "hexagonal"`) has three parts:

- `domain/`: the rules of the business. Standard library only (`domain_purity`).
- `application/`: the use cases. It uses the domain and ports (small `Protocol` interfaces) and
  never imports adapters (`layers`).
- `adapters/`: the outside world (command line, files, git, HTTP, AI models).

Folders inside each part are grouped by responsibility, at most 10 modules each.

## Tests: kinds, first, covered, sharp

- **Kinds (`test_kinds`).** Every domain and application module needs a unit test that imports it
  (`tests/unit/`, fast, no I/O). Every adapter needs an integration test (`tests/integration/`,
  real files, real git, real processes).
- **First.** Feature, fix and restore items record a failing test before any source edit, and CI
  re-checks that every new test fails on the base code (docs/decisions.md D10).
- **Covered.** At least 85% of the changed lines run under the tests (`diff-cover` against the
  base branch).
- **Sharp: mutation testing.** Coverage shows a line ran, not that a test would notice it being
  wrong. `doctrine ci mutation`:
  - takes the changed domain and application lines;
  - makes mutants of them: a comparison flipped (`>=` to `<`), a `not` dropped, a constant changed,
    a return emptied;
  - spreads up to 30 of them over the change;
  - runs the unit tests against each one in a temporary copy of the project.

  At least 70% must be caught. Each survivor is named (`file:line what changed`): write the
  assertion that would have caught it. On doctrine's own last nine merges it caught 25 of 30 in
  about a minute.

## Proof of the rules themselves

Each rule has a bad sample in [samples/python](../samples/python), and
[expectations.toml](../samples/python/expectations.toml) says which rule must catch it.
`doctrine selftest` fails if any sample slips through. A new kind of bad code is added there first,
failing, then caught.
