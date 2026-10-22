"""Group and rank corpus annotations to surface frequent or suspicious patterns."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from itertools import starmap
from pathlib import Path
from typing import override

from scripts.statistics.data import TsvCorpus, TsvWord
from scripts.statistics.token_filter import TokenFilter

MAX_PERCENTAGE = 0.01
MAX_COUNT = 5


@dataclass
class SortedAnalyses:
    """List of analyses sorted by frequency. Contains either only MWE or non-MWE."""

    analyses: list[tuple[str, int]]
    total: int

    @override
    def __str__(self) -> str:
        return "\n".join(
            f"\t\t\t{count} {count / self.total * 100:>5.1f}% {analysis}"
            for analysis, count in self.analyses
        )

    @staticmethod
    def from_dict(group: dict[str, int]) -> "SortedAnalyses":
        """Create SortedAnalyses from dict. Sort the entries by frequency."""
        return SortedAnalyses(
            sorted(group.items(), key=(lambda kv: -kv[1])),
            sum(group.values()),
        )


@dataclass
class AnalysesGroup:
    """A single group split into MWE and non-MWE analyses."""

    key: str
    mwe: SortedAnalyses
    non_mwe: SortedAnalyses
    total: int

    @override
    def __str__(self) -> str:
        s = f"{self.total} {self.key}\n"
        for analysis_type, analyses in [("NON-MWE", self.non_mwe), ("MWE", self.mwe)]:
            if analyses.total == 0:
                continue
            s += f"\t{analyses.total} {analyses.total / self.total * 100:>6.2f}% {analysis_type}\n"
            s += str(analyses) + "\n"
        return s

    @staticmethod
    def from_dict(key: str, group: dict[str, dict[str, int]]) -> "AnalysesGroup":
        """Create AnalysesGroup from dict."""
        mwe = SortedAnalyses.from_dict(group.get("[MWE]", {}))
        non_mwe = SortedAnalyses.from_dict(group.get("[NON-MWE]", {}))
        return AnalysesGroup(key, mwe, non_mwe, mwe.total + non_mwe.total)


@dataclass
class TokenGrouper:
    """Group value-mapped tokens by a key-mapping and order by frequency."""

    def __init__(
        self,
        out: Path,
        corpus: TsvCorpus,
        key_mapper: Callable[[TsvWord], str],
        value_mapper: Callable[[TsvWord], str],
    ) -> None:
        """Generate the groups and write to out."""
        self.key_mapper = key_mapper
        self.value_mapper = value_mapper
        self.groups = self.generate_groups(corpus, key_mapper, value_mapper)
        out.write_text("\n".join(str(g) for g in self.groups), encoding="utf-8")

    @staticmethod
    def generate_groups(
        corpus: TsvCorpus,
        key_mapper: Callable[[TsvWord], str],
        value_mapper: Callable[[TsvWord], str],
    ) -> list[AnalysesGroup]:
        """Generate groups of value-mapped tokens in the corpus by a key-mapping."""
        groups: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int)),
        )
        for w in corpus.words:
            key = key_mapper(w)
            value = value_mapper(w)
            if w.group:
                groups[key]["[MWE]"][value] += 1
            else:
                groups[key]["[NON-MWE]"][value] += 1

        return sorted(
            starmap(AnalysesGroup.from_dict, groups.items()),
            key=lambda x: -x.total,
        )


class SuspiciousTokenGrouper(TokenGrouper):
    """TokenGrouper that keeps groups with at least one suspicious infrequent entry."""

    @override
    @staticmethod
    def generate_groups(
        corpus: TsvCorpus,
        key_mapper: Callable[[TsvWord], str],
        value_mapper: Callable[[TsvWord], str],
    ) -> list[AnalysesGroup]:
        groups = TokenGrouper.generate_groups(corpus, key_mapper, value_mapper)

        for g in groups:
            g.non_mwe.analyses = [
                (analysis, count)
                for analysis, count in g.non_mwe.analyses
                if count <= MAX_COUNT and (count / g.total) <= MAX_PERCENTAGE
            ]
            g.mwe.total = 0  # ignore MWE entries

        return [g for g in groups if len(g.non_mwe.analyses)]

    def is_suspicious(self, w: TsvWord) -> bool:
        """Whether the token occurs in a suspicious group."""
        if w.group or "WF" in w.pos:
            return False
        key = self.key_mapper(w)
        value = self.value_mapper(w)
        for group in self.groups:
            if group.key == key:
                for analysis, _ in group.non_mwe.analyses:
                    if analysis == value:
                        return True
        return False

    def report(self, out: Path, corpus: TsvCorpus) -> None:
        """Report on the suspicious tokens in their sentence context."""
        TokenFilter(out, corpus).report(self.is_suspicious)
