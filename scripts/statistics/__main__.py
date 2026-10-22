#!/usr/bin/env python3

"""Analyse the input corpus, generate statistics, and note any suspicious patterns."""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from collections import defaultdict
from pathlib import Path

from scripts.statistics.data import TsvCorpus
from scripts.statistics.histogram import Histogram
from scripts.statistics.size import CorpusSize
from scripts.statistics.suspicious import generate_suspicious
from scripts.statistics.token_grouper import TokenGrouper
from scripts.statistics.util import to_main_pos


def generate_stats(
    corpus: TsvCorpus,
    out: Path,
    metadata: Path | None = None,
    lexicon: Path | None = None,
) -> None:
    """Generate all statistics."""
    generate_suspicious(corpus, out, lexicon)
    grouped_annotations(corpus, out)
    CorpusSize(out / "size.txt", corpus, metadata)
    histograms(corpus, out)


def grouped_annotations(corp: TsvCorpus, root: Path) -> None:
    """List and order by frequency various groupings of annotations."""
    out = root / "analyses"
    out.mkdir(parents=True, exist_ok=True)
    TokenGrouper(
        out / "lemmainpos_by_grouptok.txt",
        corp,
        lambda w: w.group_token.lower(),
        lambda w: f"‘{w.lemma}’ {to_main_pos(w.pos)}",
    )
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
        out / "main_pos_by_lem.txt",
        corp,
        lambda w: f"‘{w.lemma}’",
        lambda w: to_main_pos(w.pos),
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
        lambda w: to_main_pos(w.pos),
        lambda w: w.pos,
    )


def histograms(corp: TsvCorpus, root: Path) -> None:
    """Frequency distributions of various annotations and their characteristics."""
    out = root / "histogram"
    out.mkdir(parents=True, exist_ok=True)
    Histogram(out / "token.txt").write(w.token for w in corp.words if w.pos != "PC")
    Histogram(out / "abbr.txt").write(
        f"{w.group_token:<25} ‘{w.lemma}’" for w in corp.words if "WF=abbr" in w.pos
    )
    Histogram(out / "lemma.txt").write(w.lemma for w in corp.words if w.pos != "PC")
    Histogram(out / "pos.txt").write(w.pos for w in corp.words)
    Histogram(out / "pos_main.txt").write(to_main_pos(w.pos) for w in corp.words)
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
    parser.add_argument(
        "--lexicon",
        type=Path,
        help="Lexicon file (optional)",
    )
    args = parser.parse_args()

    corpus = TsvCorpus.load(args.input)
    args.output.mkdir(parents=True, exist_ok=True)
    generate_stats(corpus, args.output, args.metadata, args.lexicon)
