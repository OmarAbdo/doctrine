# Doctrine (installed by Omar, enforced on this machine)

Every Claude Code session on this machine runs under doctrine. Its rules are enforced by hooks you
cannot change, by git hooks and by CI; this note only tells you how to work with them.

- A refusal from doctrine says why and what to do instead. Do that. Never look for a way around a
  refusal; if you believe one is wrong, stop and tell Omar.
- In a doctrine project (a folder with doctrine.toml) every change starts with
  `doctrine item start --kind <feature|fix|restore|refactor|chore> --title "..." --scope <paths>`.
- Features, fixes and restores start with a failing test: write it, run `doctrine test`, then code.
- Say something works only after `doctrine check` passed on it. Otherwise say what is unverified.
- The outcome metric decides priorities: `doctrine metric record`. When the line stops, only
  restore items may change code.
- Finish with `doctrine item done`, push the item branch and open a pull request. CI decides.
- A new project starts with `doctrine init --name "..." --approver OmarAbdo`.
