"""Utilities for filtering on corpus tokens and writing sentence context reports."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from scripts.statistics.data import TsvCorpus, TsvWord

CONTEXT_BEFORE = 10
CONTEXT_AFTER = 3


@dataclass
class TokenFilter:
    """Write a filtered list of tokens or a report of tokens in context to a file."""

    out: Path
    corpus: TsvCorpus

    def filter(
        self,
        condition: Callable[[TsvWord], bool],
        comment: Callable[[TsvWord], str] | None = None,
        sort: Callable[[tuple[TsvWord, str]], any] | None = None,
        uniq: bool = False,
    ) -> None:
        """Filter tokens based on a given condition and write to output."""
        with self.out.open("w") as f:
            for d in self.corpus.dirs:
                written_header = False
                conditioned_words: list[tuple[TsvWord, str]] = []
                for w in d.words:
                    if condition(w):
                        if not written_header:
                            written_header = True
                            f.write(f"\n{d.name:-^40}\n")

                        cmt: str = ("\t " + comment(w)) if comment else ""
                        conditioned_words.append((w, cmt))
                if uniq:
                    conditioned_words = list(set(conditioned_words))
                if sort:
                    conditioned_words.sort(key=sort)
                for w, cmt in conditioned_words:
                    f.write(f"{w}{cmt}\n")

    def report(self, condition: Callable[[TsvWord], bool]) -> None:
        """
        Report on the condition-filtered tokens in their sentence context.
        Matching token is highlighted with >> and MWE tokens are marked with [MWE].
        """
        with self.out.open("w", encoding="utf-8") as f:
            for d in self.corpus.dirs:
                f.write(f"{d.name:-^60}\n")

                words = list(d.words)
                for i in range(len(words)):
                    w = words[i]
                    if condition(w):
                        start = max(0, i - CONTEXT_BEFORE)
                        end = min(len(words), i + CONTEXT_AFTER + 1)
                        for j in range(start, end):
                            prefix = ">> " if j == i else "   "
                            c = words[j]
                            mwe = "[MWE] " if c.group else "      "
                            word = f"{c.token:<25} {c.lemma:<25} {c.pos}"
                            f.write(f"{prefix}{mwe}{word}\n")
                        f.write("\n\n")
