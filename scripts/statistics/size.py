"""Generate a token/document count table for the corpus."""

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from scripts.statistics.data import TsvCorpus, TsvDir, TsvSplit, TsvSplits


class CorpusSize:
    """Write a formatted size report to a text file."""

    def __init__(
        self,
        out: Path,
        corpus: TsvCorpus,
        metadata: Path | None = None,
    ) -> None:
        """Generate the report and write to *out*."""
        with out.open("w", encoding="utf-8") as f:
            f.write(f"{'name':<25}{'tokens':>10}{'tokens%':>10}{'docs':>10}\n")
            CorpusSize.subcorpus_size(f, corpus.splits)
            CorpusSize.tokens_pc(f, corpus)
            if metadata:
                CorpusSize.century_size(f, corpus, metadata)
            CorpusSize.subcorpus_size(f, corpus)
            CorpusSize.subcorpus_size(f, corpus.train)
            CorpusSize.subcorpus_size(f, corpus.test)
            CorpusSize.subcorpus_size(f, corpus.dev)
            # subcorpora sorted by token count
            for sub in sorted(corpus.dirs, key=lambda d: -len(list(d.words))):
                CorpusSize.subcorpus_size(f, sub, name=lambda d: d.split)

    @staticmethod
    def write(f: TextIO, name: str, words: int, total: int, docs: int) -> None:
        """Write pad formatted row."""
        f.write(f"{name:<25}{words:>10,}{words / total:>10.2%}{docs:>10}\n")

    @staticmethod
    def tokens_pc(f: TextIO, corpus: TsvCorpus) -> None:
        """Write the PC vs word percentage for the corpus."""
        docs = len(list(corpus.docs))
        docs_containing_pc = len([
            d for d in corpus.docs if any(w.pos == "PC" for w in d.words)
        ])
        docs_containing_word = len([
            d for d in corpus.docs if any(w.pos != "PC" for w in d.words)
        ])
        docs_containing_empty = len([
            d for d in corpus.docs if any(not w.pos for w in d.words)
        ])
        toks = len(list(corpus.words))
        tagged_as_pc = len([w for w in corpus.words if w.pos == "PC"])
        tagged_as_word = len([w for w in corpus.words if w.pos != "PC"])
        empty = len([w for w in corpus.words if not w.pos])
        CorpusSize.write(f, "total", toks, toks, docs)
        CorpusSize.write(f, "word", tagged_as_word, toks, docs_containing_word)
        CorpusSize.write(f, "punctuation", tagged_as_pc, toks, docs_containing_pc)
        CorpusSize.write(f, "empty", empty, toks, docs_containing_empty)
        f.write("\n")

    @staticmethod
    def subcorpus_size(
        f: TextIO,
        corpus: TsvCorpus | TsvSplit | TsvSplits | TsvDir,
        name: Callable = lambda d: d.name,
    ) -> None:
        """Write a section header for *corpus* followed by one row per sub-item."""
        # header
        total = CorpusSize.total_header(f, corpus)
        # subcorpora sorted by token count
        for sub in sorted(corpus, key=lambda t: -len(list(t.words))):
            w = len(list(sub.words))
            d = len(list(sub.docs))
            CorpusSize.write(f, name(sub), w, total, d)
        f.write("\n")

    @staticmethod
    def total_header(
        f: TextIO,
        corpus: TsvCorpus | TsvSplit | TsvSplits | TsvDir,
    ) -> int:
        """Write a total-count header row for *corpus* and return the word count."""
        total = len(list(corpus.words))
        d = len(list(corpus.docs))
        f.write(f"{corpus.name:<25}{total:>10,}{1:>10.2%}{d:>10}\n")
        return total

    @staticmethod
    def get_datasets_per_century(metadata: Path) -> dict[str, list[str]]:
        """Parse the datasets JSON and group dataset names by their century period."""
        datasets_per_century = defaultdict(list)
        for dataset in json.loads(metadata.read_text(encoding="utf-8")):
            start, end = dataset["period"].values()
            datasets_per_century[f"{start}-{end}"].append(dataset["name"])
        return datasets_per_century

    @staticmethod
    def century_size(
        f: TextIO,
        corpus: TsvCorpus,
        metadata: Path,
    ) -> None:
        """Write token/doc counts grouped by century period."""
        CorpusSize.total_header(f, corpus)
        datasets_per_century = CorpusSize.get_datasets_per_century(metadata)

        total = len(list(corpus.words))
        century_totals: dict[str, tuple[int, int]] = {}
        for century, dirs in sorted(datasets_per_century.items()):
            words = 0
            docs = 0
            for d in corpus.dirs:
                if d.name in dirs:
                    words += len(list(d.words))
                    docs += len(list(d.docs))
            century_totals[century] = (words, docs)
            CorpusSize.write(f, century, words, total, docs)
        f.write("\n")

        # now century itself is the total, and it is broken down into subcorpora (dirs)
        for century, dirs in sorted(datasets_per_century.items()):
            total, docs = century_totals[century]
            CorpusSize.write(f, century, total, total, docs)
            for sub in sorted(corpus.dirs, key=lambda d: -len(list(d.words))):
                if sub.name in dirs:
                    words = len(list(sub.words))
                    docs = len(list(sub.docs))
                    CorpusSize.write(f, sub.name, words, total, docs)
            f.write("\n")
