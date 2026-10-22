# Roadmap: what is done, what is open, what is known to be weak

## Done (the original scope, 2026-10-22)

Readability rules, tests written first, test kinds per layer, diff coverage, mutation testing, the
outcome metric with its line stop, the eval kit (eval sets, recorded runs, the CI gate, judges and
the labelling page), hexagonal architecture rules, honest reports, small pull requests, the bot
account, the admin installation and self-update.

## Not built

- **The TypeScript profile.** Omar's decision (2026-10-22): it becomes its own doctrine later,
  so that everything is finished in Python first. When it starts, the rule table
  (`rules/rules.toml`) is the part to share. Profiles turn that table into each language's tool
  settings.
- **[#34](https://github.com/OmarAbdo/doctrine/issues/34), optional:** only the labelling page
  writes a judge's eval set. Today Claude could append made-up labels to it.

## Known weak spots (true today, on purpose or for lack of a free fix)

- **CI can't re-run AI tasks.** That would need a paid model API, and doctrine's tools never cost
  money. The evals gate trusts the recorded runs, which only `doctrine eval run` may write (#32).
- **A change to an AI task's code alone** (its model, its parsing), without a change to its prompt
  or eval set, doesn't trigger the evals gate.
- **Adapters aren't mutated.** Their integration tests are too slow to run once per mutant. The
  mutation gate covers domain and application code.
- **Command patterns can't see everything.** A write to a protected file through a script that
  builds the path from pieces isn't caught by the command policy. The protections raise the cost of
  a shortcut; CI and Omar's review are the backstop.
- **Releases are tagged by hand.** New projects pin a release tag (`vX.Y.Z`). After a change that
  projects should get, bump the version and push a tag (see docs/new-project.md, "Releases").
- **Private repositories can't be protected on GitHub Free.** A private project gets the hooks and
  local checks, but no protected main.
