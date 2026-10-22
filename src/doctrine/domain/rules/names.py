"""Names that say what a thing is: long enough, and made of words rather than abbreviations."""

import re
from dataclasses import dataclass

WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|\b|_)|[A-Z]?[a-z]+|[A-Z]+|\d+")


def words(name: str) -> list[str]:
    return [part.lower() for part in WORD.findall(name)]


@dataclass(frozen=True)
class NamePolicy:
    min_length: int
    allowed_short: frozenset[str]
    banned_words: frozenset[str]

    def problems(self, name: str) -> list[str]:
        if name in self.allowed_short or (name.startswith("__") and name.endswith("__")):
            return []
        if len(name.strip("_")) < self.min_length:
            return [f"'{name}' is shorter than {self.min_length} characters"]
        return [
            f"'{name}' uses the abbreviation '{word}'"
            for word in words(name)
            if word in self.banned_words
        ]
