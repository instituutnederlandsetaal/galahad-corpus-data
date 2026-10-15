#! /usr/bin/env python3

"""
Analyse the input corpus, generate statistics, and note any suspicious patterns.

The following files are generated:
statistics/
    suspicious/
        mwe/
            mwe_dif_lemma.txt # MWEs where the lemmas of the components differ
            mwe_dif_pos.txt # MWEs where the POS of the components differ
        nou_p/
            nou-p_lemma_no_capital.txt # NOU-P tokens without a capital in the lemma
        pc/
            words_tagged_pc.txt # tokens tagged as PC but not punctuation
            pc_not_tagged_pc.txt # punctuation tokens not tagged as PC
        roman_numerals/
            wrong_roman_numerals.txt # roman numeral tokens with wrong numerical lemma
        empty/
            lemma.txt # tokens with empty lemma
            pos.txt # tokens with empty POS
    histogram/
        token.txt # histogram of tokens (excluding PC)
        lemma.txt # histogram of lemmas (excluding PC)
        pos.txt
        pos_main.txt # POS converted to main POS. NOU-C(num=sg) => NOU-C
        group.txt # histogram of group IDs
        pc.txt # histogram of tokens where POS = PC
        token_char.txt # histogram of characters in tokens
        lemma_char.txt
        token_len.txt # histogram of token lengths
        lemma_len.txt # histogram of lemma lengths
        sentence_len.txt # histogram of sentence lengths
    analyses/
        * # various grouped analyses, e.g., tok_to_lem.txt maps tokens to their lemmas
    size.txt # token size over various categories
"""

import re
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path

from scripts.statistics.data import TsvCorpus, TsvWord
from scripts.statistics.histogram import Histogram
from scripts.statistics.size import CorpusSize
from scripts.statistics.token_filter import TokenFilter
from scripts.statistics.token_grouper import SuspiciousTokenGrouper, TokenGrouper
from scripts.statistics.util import pos_to_main_pos, roman_to_int
from scripts.util.config import PUNCTUATION


def generate_stats(corpus: TsvCorpus, out: Path, metadata: Path | None = None) -> None:
    """Generate all statistics."""
    generate_suspicious(corpus, out)
    grouped_annotations(corpus, out)
    CorpusSize(out / "size.txt", corpus, metadata)
    histograms(corpus, out)


def generate_suspicious(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious patterns for manual review."""
    out = root / "suspicious"
    out.mkdir(parents=True, exist_ok=True)
    suspicious_analyses(corpus, out)
    sus_roman_numerals(corpus, out)
    sus_mwe(corpus, out)
    sus_nou_p(corpus, out)
    empty_words(corpus, out)
    sus_punctuation(corpus, out)


def suspicious_analyses(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious annotations based on a grouping of other annotations."""
    out = root / "analyses"
    out.mkdir(parents=True, exist_ok=True)
    SuspiciousTokenGrouper(
        out / "sus_lem_by_tokpos.txt",
        corpus,
        lambda w: f"{w.token.lower()} {w.pos}",
        lambda w: f"‘{w.lemma}’",
    ).report(out / "sus_lem_by_tokpos_report.txt", corpus)
    SuspiciousTokenGrouper(
        out / "sus_pos_by_toklem.txt",
        corpus,
        lambda w: f"{w.token.lower()} ‘{w.lemma}’",
        lambda w: w.pos,
    ).report(out / "sus_pos_by_toklem_report.txt", corpus)
    SuspiciousTokenGrouper(
        out / "sus_tok_by_lempos.txt",
        corpus,
        lambda w: f"‘{w.lemma}’ {w.pos}",
        lambda w: w.token.lower(),
    )  # Note: no report as it is huge


def sus_roman_numerals(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious Roman numeral tokens with incorrect lemma."""

    def convert_w(w: TsvWord) -> int:
        if w.group:
            concat = ".".join(m.token for m in w.mwe)
            return roman_to_int(concat)
        return roman_to_int(w.token)

    out = root / "roman_numerals"
    out.mkdir(parents=True, exist_ok=True)
    TokenFilter(out / "wrong_roman_numerals.txt", corpus).filter(
        lambda w: (
            "representation=rom" in w.pos
            and str(convert_w(w)) != w.lemma
            and re.match(r"[0-9]", w.lemma) is not None
        ),
        comment=lambda w: f"converted='{convert_w(w)}'",
    )


def sus_mwe(corpus: TsvCorpus, root: Path) -> None:
    """
    Suspicious multi-word expressions (MWEs).
    MWE's where lemmata or POS differ, or where the group size is 1 (i.e., not a MWE).
    """
    out = root / "mwe"
    out.mkdir(parents=True, exist_ok=True)
    TokenFilter(out / "mwe_dif_lemma.txt", corpus).filter(
        lambda w: any(m.lemma != w.lemma for m in w.mwe),
    )
    TokenFilter(out / "mwe_dif_pos.txt", corpus).filter(
        lambda w: any(m.pos != w.pos for m in w.mwe),
    )
    TokenFilter(out / "lonely_mwe.txt", corpus).filter(lambda w: len(w.mwe) == 1)


def sus_nou_p(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious NOU-P tokens without a capital in the lemma."""
    out = root / "nou_p"
    out.mkdir(parents=True, exist_ok=True)
    TokenFilter(out / "nou-p_lemma_no_capital.txt", corpus).filter(
        lambda w: w.pos == "NOU-P" and not any(c.isupper() for c in w.lemma),
    )


def histograms(corp: TsvCorpus, root: Path) -> None:
    """Frequency distributions of various annotations and their characteristics."""
    out = root / "histogram"
    out.mkdir(parents=True, exist_ok=True)
    Histogram(out / "token.txt").write(w.token for w in corp.words if w.pos != "PC")
    Histogram(out / "lemma.txt").write(w.lemma for w in corp.words if w.pos != "PC")
    Histogram(out / "pos.txt").write(w.pos for w in corp.words)
    Histogram(out / "pos_main.txt").write(pos_to_main_pos(w.pos) for w in corp.words)
    Histogram(out / "group.txt").write(w.group for w in corp.words)
    Histogram(out / "pc.txt").write(w.token for w in corp.words if w.pos == "PC")
    Histogram(out / "token_char.txt").write(
        c for w in corp.words for c in w.token if w.pos != "PC"
    )
    Histogram(out / "lemma_char.txt").write(
        c for w in corp.words for c in w.lemma if w.pos != "PC"
    )
    Histogram(out / "sentence_len.txt").write(str(len(s.words)) for s in corp.sents)
    Histogram(out / "token_len.txt").write(str(len(w.token)) for w in corp.words)
    Histogram(out / "lemma_len.txt").write(str(len(w.lemma)) for w in corp.words)


def sus_punctuation(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious tokens that should or should not be punctuation."""
    out = root / "pc"
    out.mkdir(parents=True, exist_ok=True)
    TokenFilter(out / "words_tagged_pc.txt", corpus).filter(
        lambda w: w.pos == "PC" and re.fullmatch(PUNCTUATION, w.token) is None,
    )
    TokenFilter(out / "pc_not_tagged_pc.txt", corpus).filter(
        lambda w: re.fullmatch(PUNCTUATION, w.token) is not None and w.pos != "PC",
    )


def empty_words(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious tokens with empty lemma or POS."""
    out = root / "empty"
    out.mkdir(parents=True, exist_ok=True)
    TokenFilter(out / "lemma.txt", corpus).filter(lambda w: not w.lemma)
    TokenFilter(out / "pos.txt", corpus).filter(lambda w: not w.pos)
    TokenFilter(out / "pos_report.txt", corpus).report(lambda w: not w.pos)
    TokenFilter(out / "lemma_report.txt", corpus).report(lambda w: not w.lemma)


def grouped_annotations(corp: TsvCorpus, root: Path) -> None:
    """List and order by frequency various groupings of annotations."""
    out = root / "analyses"
    out.mkdir(parents=True, exist_ok=True)
    TokenGrouper(
        out / "lem_by_tok.txt",
        corp,
        lambda w: w.token.lower(),
        lambda w: f"‘{w.lemma}’",
    )
    TokenGrouper(
        out / "pos_by_tok.txt",
        corp,
        lambda w: w.token.lower(),
        lambda w: w.pos,
    )
    TokenGrouper(
        out / "lempos_by_tok.txt",
        corp,
        lambda w: w.token.lower(),
        lambda w: f"‘{w.lemma}’ {w.pos}",
    )
    TokenGrouper(
        out / "tok_by_lem.txt",
        corp,
        lambda w: f"‘{w.lemma}’",
        lambda w: w.token.lower(),
    )
    TokenGrouper(
        out / "pos_by_lem.txt",
        corp,
        lambda w: f"‘{w.lemma}’",
        lambda w: w.pos,
    )
    TokenGrouper(
        out / "tokpos_by_lem.txt",
        corp,
        lambda w: f"‘{w.lemma}’",
        lambda w: f"{w.token.lower()} {w.pos}",
    )
    TokenGrouper(
        out / "tok_by_pos.txt",
        corp,
        lambda w: w.pos,
        lambda w: w.token.lower(),
    )
    TokenGrouper(
        out / "lem_by_pos.txt",
        corp,
        lambda w: w.pos,
        lambda w: f"‘{w.lemma}’",
    )
    TokenGrouper(
        out / "toklem_by_pos.txt",
        corp,
        lambda w: w.pos,
        lambda w: f"{w.token.lower()} ‘{w.lemma}’",
    )
    TokenGrouper(
        out / "tok_by_lempos.txt",
        corp,
        lambda w: f"‘{w.lemma}’ {w.pos}",
        lambda w: w.token.lower(),
    )
    TokenGrouper(
        out / "pos_by_toklem.txt",
        corp,
        lambda w: f"{w.token.lower()} ‘{w.lemma}’",
        lambda w: w.pos,
    )
    TokenGrouper(
        out / "lem_by_tokpos.txt",
        corp,
        lambda w: f"{w.token.lower()} {w.pos}",
        lambda w: f"‘{w.lemma}’",
    )
    TokenGrouper(
        out / "pos_by_main_pos.txt",
        corp,
        lambda w: pos_to_main_pos(w.pos),
        lambda w: w.pos,
    )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Print statistics about a dataset",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="TSV dir")
    parser.add_argument("output", type=Path, help="Stats dir")
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Metadata file (optional)",
    )
    args = parser.parse_args()

    corpus = TsvCorpus.load(args.input)
    args.output.mkdir(parents=True, exist_ok=True)
    generate_stats(corpus, args.output, args.metadata)
