# Decisions

Each record says what was decided, when and by whom, why, what was rejected, and where it lives.
To change a decision: agree it with Omar, change the code through an item, and record the new
decision here, keeping the old one struck through below it.

## D1. Enforce by machinery; CLAUDE.md is only a map

- **When, who:** 2026-10-21, Omar and Claude, after studying HQ.
- **What:** every rule runs as code: Claude Code hooks, a git hook, CI and branch protection.
  CLAUDE.md files only say where things are and how to work with the refusals.
- **Why:** HQ had written rules, invariants and 394 tests, and still drifted. Advice loses under
  pressure; a refusal doesn't.
- **Rejected:** a better CLAUDE.md, review checklists, "be careful" instructions.
- **Where:** `src/doctrine/adapters/claude/` (hooks), `policy/` (installer, admin settings),
  `.github/workflows/`.

## D2. Admin-owned installation with managed hooks

- **When, who:** 2026-10-21, Claude, approved by Omar.
- **What:** doctrine installs to `C:\Program Files\Doctrine`. Its hooks are set in
  `C:\Program Files\ClaudeCode\managed-settings.json` with `allowManagedHooksOnly`. Both folders
  need administrator rights to change, and Claude never runs elevated (the `elevation` rule).
- **Why:** a rule Claude can edit is a suggestion. Admin-owned files are out of its reach.
- **Rejected:** a separate Windows account for Claude (Omar: not needed; admin ownership is
  enough); hooks in user settings (Claude could edit those).

## D3. Approvals only for loosening; overrides only by approving a pull request

- **When, who:** 2026-10-21, Omar.
- **What:** tightening a limit, adding tests or adding eval cases is free. Loosening anything
  (limits, exceptions, the outcome, an AI task's minimum, a judge turned plain, eval labels, guarded
  files) waits for Omar's approval of that exact commit. There is no override in chat, no
  environment switch and no `--force`.
- **Why:** Omar is busy and automates to save time ("that's exactly why I'm automating stuff"), so
  approvals must be rare and phone-sized. A chat override would be the leak the framework exists to
  close.
- **Where:** `domain/governance/goalposts.py`, `adapters/cli/gates/ci_commands.py`.

## D4. A bot account does all of Claude's GitHub work

- **When, who:** 2026-10-21, Omar created `OmarAbdosBot`.
- **What:** commits, pushes and pull requests are made as the bot, through a token in the admin
  settings' environment (`GH_TOKEN`, with a git credential helper). The bot is a write
  collaborator; only Omar approves.
- **Why:** GitHub doesn't let an author approve their own pull request. With Claude working as
  Omar, his approval couldn't count.

## D5. The repository is public

- **When, who:** 2026-10-21, Omar.
- **What:** `OmarAbdo/doctrine` is public.
- **Why:** GitHub Free gives branch protection to public repositories only, and doctrine's main
  must be protected: it is what every PC installs.
- **Consequence:** a private project on GitHub Free can't have a protected main (docs/roadmap.md).

## D6. Main is protected and pull requests merge themselves

- **What:** main needs a pull request, the `self` check, and one approval (Omar's) on the latest
  commit. Stale approvals are dismissed, admins included, history linear, no force pushes. When
  every gate passes, `merge.yml` squash-merges with the repository's own token. Claude never merges
  (the `github-admin` rule).
- **Why:** the merge is decided by checks on the committed result and Omar's approval, not by the
  session that wrote the code.

## D7. Doctrine updates itself from protected main

- **When, who:** 2026-10-22 (#6, #16), Claude, approved by Omar.
- **What:** the "Doctrine update" scheduled task (SYSTEM, every 30 minutes and at startup)
  downloads main's head and builds a new release folder. The release's self-test must catch
  everything before the admin settings switch to it. Each new release installs itself with its own
  installer code.
- **Why:** Omar shouldn't have to run an admin installer after every merge. Since main only
  changes with Omar's approval, installing it is safe.
- **Rejected:** re-running the installer by hand (it's now only needed to change the bot token).

## D8. One rule table for every language

- **When, who:** 2026-10-21, Omar ("one place, not Python and TS in different places").
- **What:** `rules/rules.toml` holds every limit, ban and naming rule once. Each language profile
  turns it into its tools' settings, so no tool config can drift from it.
- **Limits:** set by Omar on 2026-10-21. Functions ≤ 40 lines, complexity ≤ 7, nesting ≤ 2,
  parameters ≤ 4, files ≤ 300 lines, folders ≤ 10 modules, names of real words.

## D9. TypeScript gets its own doctrine later

- **When, who:** 2026-10-22, Omar: "make it in its own doctrine later so that we can finish
  everything with python nicely".
- **What:** this repository is Python only. The rule table is what a TypeScript doctrine would
  share.

## D10. Tests come first, and CI proves it

- **What:** a feature, fix or restore item can't change source code before a failing test was
  recorded (`doctrine test` while red). In CI, every new test must fail on the base branch's code
  (the `red-first` gate runs them in a git worktree of the base).
- **Why:** a test written after the code tends to test what the code does, not what it should do.
  The recorded red run alone could be gamed, so CI checks again on the committed result.
- **Where:** `application/guard.py`, `adapters/cli/gates/red_first.py`.

## D11. Hexagonal architecture, with test kinds per layer

- **What:** each service has `domain` (standard library only), `application` (uses the domain and
  ports) and `adapters` (the outside world). Domain and application modules need a unit test;
  adapters need an integration test. Inheritance from project classes is limited to one level,
  interfaces to five methods.
- **Why:** HQ's one-folder layout made every change's reach unknowable. With layers, a change's
  blast radius is visible in its imports.

## D12. An outcome metric with a line stop

- **What:** every project names one number it exists to move, with a command that computes it
  from real data and a stop value. When `doctrine metric record` falls under the stop value, only
  `restore` items may change code until it recovers. The line arms at launch: until a recorded
  value has reached the stop value, nothing stops it (2026-10-22, #46). A project that hasn't
  shipped measures 0 and would otherwise stop its own line on its first record.
- **Why:** HQ shipped 95 commits while its number fell to 0. Activity is not progress.
- **Doctrine's own metric:** the share of bad samples and bypass attempts its self-test catches
  (it stops below 1).

## D13. Small pull requests, built in

- **When, who:** 2026-10-22 (#19), Omar asked for it to be built in.
- **What:** an item may change at most 400 lines (added plus removed) and 15 files. A
  line-ending-only change counts for nothing (#29).
- **Why:** Omar reviews from his phone. A small pull request gets a real review.

## D14. Every pull request says what changed, why, the proof, and what is not verified

- **When:** 2026-10-22 (#20).
- **What:** the `description` gate refuses a pull request without those four sections filled in.
  Placeholders and HTML comments count as empty.
- **Why:** "honest reports". The "Not verified" section is where unproven claims have to go,
  instead of into a summary that says everything works.

## D15. Honest claims at the end of a turn

- **What:** when Claude's final message claims success ("fixed", "verified", "passes") while the
  changes since the last passing `doctrine check` are unchecked, the Stop hook sends it back to
  work. After three refusals in a row the turn may end, and the override is recorded as evidence.
- **Why:** an unverified "it works" is how HQ's reports drifted from reality. The limit of three
  keeps a session from being trapped in a loop.

## D16. Evals: recorded per version, gated in CI, judges scored against Omar's labels

- **When:** 2026-10-22 (#10, #22, #25, #27, #30–#33, #36).
- **What:**
  - An AI task's prompt and eval set are fingerprinted (content digests that ignore CRLF).
  - A change to either needs a recorded run on the new version that holds the task's minimum.
  - A lower score than before on the same eval set waits for Omar.
  - A judge is scored by the lower of two rates: the share of Omar's passes it passes, and the
    share of his fails it fails.
- **Why:** this is Hamel's loop. Look at real outputs, label them, measure every change, and trust
  a judge only as far as it agrees with the human. Plain accuracy flatters a judge that passes
  everything when most outputs pass.
- **Rejected:** re-running tasks in CI (it needs a paid API, and tools never cost money); AI
  summaries of traces on the labelling page (Omar does the judging).

## D17. Mutation testing on changed domain and application code

- **When:** 2026-10-22 (#11, #23, #35).
- **What:** up to 30 mutants, spread over the changed lines, each run against the unit tests in a
  copy of the project. At least 70% must be caught.
- **Why:** coverage shows a line ran; a caught mutant shows a test would notice the line being
  wrong.
- **Rejected:** mutating adapters (their integration tests are too slow); mutating everything
  (minutes per pull request matter).

## D18. Tools never cost money

- **Who:** Omar (a standing rule across his projects).
- **What:** no paid APIs, tiers or budgets. Local or free only: pinned open-source tools with
  hashed downloads, GitHub Free, GitHub Actions on a public repository.

## D19. Work items are the unit of change

- **What:**
  - Every change starts with `doctrine item start`, with a kind, a title and a scope. The file
    lives in `work/`, and the branch is `item/<id>-<title>`.
  - Item numbers are unique across all branches.
  - Edits outside the scope are refused.
  - `work/` and `metrics/` are written by doctrine commands only.
  - Evidence (test runs, checks, overrides) goes to `.doctrine/evidence.jsonl`.
- **Why:** one item, one reviewable purpose. It also tells a session with no memory exactly what
  it may touch.

## D20. Line endings: LF everywhere, and endings don't count

- **When, who:** 2026-10-22, Omar chose this over an approval exception (#29, #37).
- **What:** `.gitattributes` stores text with LF (batch files keep CRLF). The size gate ignores
  carriage returns at line ends.
- **Rejected:** letting oversized items through with an approval. That would have created an
  exception path for a problem that could be solved without one.
