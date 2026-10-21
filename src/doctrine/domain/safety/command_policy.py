"""Which shell commands would get around a gate: skipped hooks, pushes past review, admin powers.

The threat is a capable assistant under pressure taking a shortcut, not an attacker. Every refusal
names the rule and what to do instead, so the shortcut is never the easier path.
"""

import re
from dataclasses import dataclass

from doctrine.domain.safety.protected import mentions_protected

MAIN_BRANCHES = frozenset({"main", "master"})

WRITES = re.compile(
    r"(>|\btee\b|\bsed\s+-i|\bperl\s+-i|\bset-content\b|\badd-content\b|\bout-file\b|\bnew-item\b|"
    r"\bremove-item\b|\brm\b|\bdel\b|\bmv\b|\bcp\b|\bcopy-item\b|\bmove-item\b|\bicacls\b|"
    r"\btakeown\b|\battrib\b|\btruncate\b|\bpython\S*\s+-c\b|\bgit\s+(checkout|restore)\b)",
    re.IGNORECASE,
)

RULES = (
    (
        "skip-hooks",
        re.compile(
            r"--no-verify\b|\bgit\b.*\bcommit\b.*\s-[a-z]*n[a-z]*\b|"
            r"\b(SKIP|HUSKY|PRE_COMMIT_ALLOW_NO_CONFIG)=",
            re.IGNORECASE,
        ),
        "commit hooks are the gate; fix what they report instead of skipping them",
    ),
    (
        "hooks-path",
        re.compile(r"core\.hookspath", re.IGNORECASE),
        "the hooks folder is fixed; fix what the hooks report instead of moving them",
    ),
    (
        "force-push",
        re.compile(r"\bgit\s+push\b.*(--force(?!-with-lease)\b|\s-f\b|\s\+\S)"),
        "history is never rewritten by force; use --force-with-lease on your item branch",
    ),
    (
        "github-admin",
        re.compile(
            r"\bgh\s+(pr\s+merge|repo\s+(edit|delete|rename|archive)|secret|"
            r"ruleset|api\b.*(-X\s*(PUT|PATCH|DELETE)|protection|rulesets|"
            r"collaborators|actions/permissions|/hooks|/keys))",
            re.IGNORECASE,
        ),
        "merging and repository settings belong to the pipeline and Omar; open a pull request",
    ),
    (
        "credentials",
        re.compile(
            r"\bgh\s+auth\s+(token|login|refresh|switch)|\bgit\s+credential\b|"
            r"\bcmdkey\b|get-storedcredential|\.git-credentials",
            re.IGNORECASE,
        ),
        "credentials are not yours to read or switch; work with the account you were given",
    ),
    (
        "elevation",
        re.compile(r"-verb\s+runas|\brunas\b|\bsudo\b", re.IGNORECASE),
        "nothing here needs administrator rights; ask Omar if you think it does",
    ),
    (
        "doctrine-override",
        re.compile(r"\bDOCTRINE_[A-Z_]*="),
        "doctrine has no off switch; fix what it reports",
    ),
)


@dataclass(frozen=True)
class CommandContext:
    current_branch: str
    in_project: bool


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    rule: str = ""
    reason: str = ""


ALLOWED = Verdict(allowed=True)

PROJECT_RULES = (
    (
        "push-main",
        re.compile(r"\bgit\s+push\b.*[\s:/](main|master)(\s|$)"),
        "main changes only through a reviewed pull request; push your item branch",
    ),
)


def touches_protected_path(command: str) -> bool:
    return mentions_protected(command) and WRITES.search(command) is not None


def on_main(command: str, context: CommandContext) -> bool:
    commits_or_pushes = re.search(r"\bgit\s+(commit|push)\b", command) is not None
    return commits_or_pushes and context.current_branch in MAIN_BRANCHES


def judge_command(command: str, context: CommandContext) -> Verdict:
    """The rules that hold everywhere, then, inside a doctrine project, those protecting main."""
    rules = (*RULES, *PROJECT_RULES) if context.in_project else RULES
    for rule, pattern, advice in rules:
        if pattern.search(command):
            return Verdict(allowed=False, rule=rule, reason=f"Refused ({rule}): {advice}.")
    if touches_protected_path(command):
        return Verdict(
            allowed=False,
            rule="protected-path",
            reason="Refused (protected-path): doctrine's own files change only through "
            "an approved pull request to the doctrine repository.",
        )
    if context.in_project and on_main(command, context):
        return Verdict(
            allowed=False,
            rule="main-branch",
            reason="Refused (main-branch): work happens on an item branch; "
            "start one with `doctrine item start`.",
        )
    return ALLOWED
