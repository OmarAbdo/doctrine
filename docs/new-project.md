# Starting a new project from doctrine

**Who:** Omar decides the project and its outcome. Claude does the rest, except the GitHub
settings, which are Omar's (Claude's `gh` calls on repository settings are refused).
**When:** before the first line of the project's code.

## 1. Create it (Claude)

In an empty folder:

```
doctrine init --name "Job Hunter" --approver OmarAbdo
```

This copies `templates/python-hexagonal`:

- `doctrine.toml`: the contract;
- `src/<package>/{domain,application,adapters}`;
- `tests/{unit,integration,acceptance}`;
- `evals/`, `metrics/`, `work/`;
- `CLAUDE.md`, the pull request template;
- the `doctrine`, `doctrine-merge` and `doctrine-approval` workflows.

It also runs `git init -b main` and installs the `pre-commit` hook. The package name comes from
the project name (`job_hunter`).

## 2. GitHub (Omar, one command)

In the project's folder, with `gh` logged in as `OmarAbdo`:

```
powershell -ExecutionPolicy Bypass -File "D:\1 Software\Small tools\Doctrine\policy\new-project-github.ps1" -Name hunter
```

[policy/new-project-github.ps1](../policy/new-project-github.ps1) does every step, and running it
again changes nothing:

- commits the template if nothing is committed yet;
- creates the repository as public (needed to protect main on GitHub Free; docs/decisions.md D5)
  and pushes main;
- allows squash merges only;
- adds `OmarAbdosBot` as a writer and accepts the invitation with the bot's token from the admin
  settings;
- protects main: a pull request with 1 approval (stale approvals dismissed), the check
  `gates / gates`, administrators included, linear history, no force pushes.

It is Omar's to run because Claude's `gh` calls on repository settings are refused on purpose. No
secret is needed: doctrine is public, so CI reads it with the project's own token.

## 3. The first item: the outcome metric (Omar and Claude)

`doctrine.toml` starts with `metric = "not defined yet"`. The first item agrees with Omar the one
number the project exists to move:

- a command that computes it from real data and prints it;
- a baseline;
- `stop_below`, the value under which the line stops.

Record it with `doctrine metric record`, even while it is 0. The line arms once a recorded value
reaches the stop value, so recording 0 before launch doesn't stop it (#46). Everything after
launch is judged against it.

## 4. AI tasks

If the project uses a model, declare each prompt as an `[[ai_tasks]]` entry with an eval set
before it ships (docs/evals.md). Log real traces from day one: they are what Omar labels.

## Pinning: which doctrine a project runs

The project's `.github/workflows/doctrine.yml` calls
`OmarAbdo/doctrine/.github/workflows/project-gates.yml@v<version>`. Its `doctrine.toml` has
`doctrine_version`, the version of doctrine that created it. The CI gates are therefore the ones of
that release tag. The hooks on the PC are always the newest release.

**To move a project to a newer doctrine:** change both the workflow's tag and `doctrine_version`
in one item. Both are guarded, so Omar approves it.

## Releases (doctrine maintainers)

New projects pin the version in `src/doctrine/__init__.py` and `pyproject.toml`, so that version
must exist as a tag:

1. Bump the version in both files through an item, after the changes projects should get.
2. When it merges, `.github/workflows/release.yml` tags main's commit `v<version>` by itself (#44).
   By hand, if ever needed: `git tag v0.2.0 && git push origin v0.2.0` from the merged main (a
   tags-only push from main is allowed).
