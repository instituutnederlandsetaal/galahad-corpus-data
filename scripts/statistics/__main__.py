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

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path

from scripts.statistics.data import TsvCorpus
from scripts.statistics.histogram import Histogram
from scripts.statistics.size import CorpusSize
from scripts.statistics.suspicious import generate_suspicious
from scripts.statistics.token_filter import TokenFilter
from scripts.statistics.token_grouper import TokenGrouper
from scripts.statistics.util import to_main_pos


def generate_stats(
    corpus: TsvCorpus,
    out: Path,
    metadata: Path | None = None,
    lexicon: Path | None = None,
) -> None:
    """Generate all statistics."""
    TokenFilter(out / "sluistekens.txt", corpus).report(
        lambda w: "|" in w.lemma or "|" in w.pos,
    )
    generate_suspicious(corpus, out, lexicon)
    grouped_annotations(corpus, out)
    CorpusSize(out / "size.txt", corpus, metadata)
    histograms(corpus, out)


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
        lambda w: to_main_pos(w.pos),
        lambda w: w.pos,
    )


def histograms(corp: TsvCorpus, root: Path) -> None:
    """Frequency distributions of various annotations and their characteristics."""
    out = root / "histogram"
    out.mkdir(parents=True, exist_ok=True)
    Histogram(out / "token.txt").write(w.token for w in corp.words if w.pos != "PC")
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
