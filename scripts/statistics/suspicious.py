"""Find suspicious tokens for manual review."""

import re
from collections import defaultdict
from pathlib import Path

from scripts.statistics.data import TsvCorpus, TsvWord
from scripts.statistics.token_filter import TokenFilter
from scripts.statistics.token_grouper import SuspiciousTokenGrouper
from scripts.statistics.util import roman_to_int, to_main_pos
from scripts.util.config import PUNCTUATION


def generate_suspicious(
    corpus: TsvCorpus,
    root: Path,
    lexicon: Path | None = None,
) -> None:
    """Suspicious patterns for manual review."""
    out = root / "suspicious"
    out.mkdir(parents=True, exist_ok=True)
    suspicious_analyses(corpus, out)
    sus_roman_numerals(corpus, out)
    sus_mwe(corpus, out)
    sus_nou_p(corpus, out)
    empty_words(corpus, out)
    sus_punctuation(corpus, out)
    if lexicon is not None:
        lexicon_based_checks(corpus, out, lexicon)


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
    TokenFilter(out / "lonely_mwe_report.txt", corpus).report(lambda w: len(w.mwe) == 1)


def sus_nou_p(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious NOU-P tokens without a capital in the lemma."""
    out = root / "nou_p"
    out.mkdir(parents=True, exist_ok=True)
    TokenFilter(out / "nou-p_lemma_no_capital.txt", corpus).filter(
        lambda w: w.pos == "NOU-P" and not any(c.isupper() for c in w.lemma),
    )


def empty_words(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious tokens with empty lemma or POS."""
    out = root / "empty"
    out.mkdir(parents=True, exist_ok=True)
    TokenFilter(out / "lemma.txt", corpus).filter(lambda w: not w.lemma)
    TokenFilter(out / "pos.txt", corpus).filter(lambda w: not w.pos)
    TokenFilter(out / "pos_report.txt", corpus).report(lambda w: not w.pos)
    TokenFilter(out / "lemma_report.txt", corpus).report(lambda w: not w.lemma)


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

