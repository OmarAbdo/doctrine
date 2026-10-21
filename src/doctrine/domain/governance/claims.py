"""Success claims in a final message ("fixed", "verified", "all tests pass") that need proof."""

import re

CLAIM = re.compile(
    r"\b(fixed|verified|works|working|done|pass|passes|passed|passing|resolved|proven|confirmed)\b",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"\b(not|no|never|nothing|n't|isn't|aren't|haven't|hasn't|don't|doesn't|"
    r"didn't|won't|until|yet)\b",
    re.IGNORECASE,
)
WINDOW_WORDS = 4


def negated(text_before: str) -> bool:
    nearby = " ".join(text_before.split()[-WINDOW_WORDS:])
    return NEGATION.search(nearby) is not None or nearby.lower().endswith("n't")


def sentence_claims(sentence: str) -> list[str]:
    return [
        match.group(1).lower()
        for match in CLAIM.finditer(sentence)
        if not negated(sentence[: match.start()])
    ]


def success_claims(message: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?;:])\s+|\n+", message)
    return [claim for sentence in sentences for claim in sentence_claims(sentence)]
