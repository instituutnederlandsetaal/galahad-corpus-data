"""Find suspicious tokens for manual review."""

import re
from collections import defaultdict
from pathlib import Path

from scripts.statistics.data import TsvCorpus, TsvWord
from scripts.statistics.ngram import SuspiciousNgrams
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
    SuspiciousNgrams(corpus, out / "sus_ngrams_report.txt").report()
    suspicious_analyses(corpus, out)
    sus_roman_numerals(corpus, out)
    sus_mwe(corpus, out)
    sus_nou_p(corpus, out)
    empty_words(corpus, out)
    sus_punctuation(corpus, out)
    sus_lemma(corpus, out)
    sus_abbr(corpus, out)
    sus_pos(corpus, out)
    if lexicon is not None:
        lexicon_based_checks(corpus, out, lexicon)


def sus_pos(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious POS tags."""
    out = root / "pos"
    out.mkdir(parents=True, exist_ok=True)
    sus_noun_distance(corpus, out)
    sus_aa_free(corpus, out)


def sus_aa_free(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious AA-free patterns."""
    out = root / "sus_aa_free.txt"
    f = out.open("w", encoding="utf-8")
    for dir in corpus:
        f.write(f"{dir.name:-^30}\n")
        words = list(dir.words)
        for i, w in enumerate(words):
            if (
                "AA(degree=pos,position=free" in w.pos
                and w.lemma not in {"vol", "alleen"}
                and "+" not in w.pos
            ):
                next = words[i + 1] if i + 1 < len(words) else None
                if next is not None and "NOU-C" in next.pos and "+" not in next.pos:
                    # suspicious!
                    WINDOW = 7
                    context = words[
                        max(0, i - WINDOW) : min(len(words), i + WINDOW)
                    ]  # 7 words before and after
                    for i, cw in enumerate(context):
                        if i == WINDOW:
                            f.write(f">> {cw}\n")
                        else:
                            f.write(f"   {cw}\n")
                    f.write("\n")  # space between context windows


def sus_noun_distance(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious noun distance patterns."""
    out = root / "sus_noun_distance.txt"
    f = out.open("w", encoding="utf-8")
    for dir in corpus:
        f.write(f"{dir.name:-^30}\n")
        words = list(dir.words)
        report: list[tuple[TsvWord, int]] = []
        for i, w in enumerate(words):
            if "prenom" in w.pos and w.lemma not in {"de+een", "de+ander"}:
                # get the index in the w.pos string of prenom and check if there exists a NOU later in the w.to_main_pos
                prenom_index = w.pos.find("prenom")
                nou_index = w.pos.find("NOU")
                noun_dist = -1
                if nou_index > prenom_index:
                    noun_dist = 0
                if noun_dist == -1:
                    # look further
                    for j in range(1, len(words) - i):
                        neighbour = words[i + j]
                        if "NOU" in neighbour.pos or "NUM" in neighbour.pos:
                            noun_dist = j
                            break
                    # look back (until current noun_dist) and commit if closer
                    for j in range(1, i + 1):
                        if j > noun_dist:
                            break  # no need to look further back than the current closest noun
                        neighbour = words[i - j]
                        if "NOU" in neighbour.pos or "NUM" in neighbour.pos:
                            noun_dist = j
                            break
                # still no match, report
                if noun_dist > 1:  # thats unusual
                    # save context
                    WINDOW = 10
                    context = words[
                        max(0, i - WINDOW) : i + WINDOW
                    ]  # 5 words before and after
                    report.append((w, noun_dist, context))
        # sort by dist
        report.sort(key=lambda x: x[1])
        for w, dist, context in report:
            if dist >= 8:
                for i, cw in enumerate(context):
                    if i == WINDOW:
                        f.write(f">> {cw}\n")
                    elif "NOU" in cw.pos or "NUM" in cw.pos:
                        f.write(f"»  {cw}\n")
                    else:
                        f.write(f"   {cw}\n")
                f.write("\n")  # add a blank line after each context for readability


def sus_lemma(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious lemmas with weird characters or patterns."""
    out = root / "lemma"
    out.mkdir(parents=True, exist_ok=True)
    lemma_weird_chars(corpus, out)
    largest_diff_token_lemma(corpus, out)


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
        out / "sus_lem_by_tok.txt",
        corpus,
        lambda w: w.token.lower(),
        lambda w: f"‘{w.lemma}’",
    ).report(out / "sus_lem_by_tok_report.txt", corpus)
    SuspiciousTokenGrouper(
        out / "sus_pos_by_toklem.txt",
        corpus,
        lambda w: f"{w.token.lower()} ‘{w.lemma}’",
        lambda w: w.pos,
    ).report(out / "sus_pos_by_toklem_report.txt", corpus)
    SuspiciousTokenGrouper(
        out / "sus_pos_by_tok.txt",
        corpus,
        lambda w: w.token.lower(),
        lambda w: w.pos,
    ).report(out / "sus_pos_by_tok_report.txt", corpus)
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
        sort=lambda w: f"{w[0].lemma}{w[0].group}",
        group=True,
    )
    TokenFilter(out / "mwe_dif_pos.txt", corpus).filter(
        lambda w: any(m.pos != w.pos for m in w.mwe),
        sort=lambda w: f"{w[0].lemma}{w[0].group}",
        group=True,
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


def lemma_weird_chars(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious characters in lemmata."""
    # manual pattern is fine for now. Gives us an explicit idea of what's used
    patt = r"[^ \-a-zA-Z0-9'+|.ëïüéóàçöøáÖèêüñäíô/âúłżšÉ—ŽČýő]"
    TokenFilter(root / "lemmata-with-weird-chars.txt", corpus).filter(
        lambda w: (
            re.search(patt, w.lemma) is not None
            and to_main_pos(w.pos) not in {"PC", "RES"}
        ),
    )


def load_lexicon(lexicon: Path) -> tuple[set[str], dict[str, set[str]]]:
    # load in lexicon
    entries: set[tuple[str, str]] = {
        tuple(line.strip("\n").split("\t")) for line in Path(lexicon).open()
    }
    lemmata = {e[0] for e in entries}
    # dict with pos as key and lemmata sets as values
    pos_to_lemmata: dict[str, set[str]] = defaultdict(set)
    for lemma, pos in entries:
        pos_to_lemmata[pos].add(lemma)
    # All VRB lemmata are valid NOU-C lemmata
    pos_to_lemmata["NOU-C"].update(pos_to_lemmata["VRB"])
    return lemmata, pos_to_lemmata


def lexicon_based_checks(corpus: TsvCorpus, root: Path, lexicon: Path) -> None:
    """Checks based on a lexicon."""
    out = root / "lexicon"
    out.mkdir(parents=True, exist_ok=True)
    lemmata, pos_to_lemmata = load_lexicon(lexicon)

    TokenFilter(out / "unknown_lemmata.txt", corpus).filter(
        lambda w: (
            any(lemma not in lemmata for lemma in re.split(r"[|+]", w.lemma))
            and not any(
                pos in {"PC", "NOU-P", "RES", "NUM"}
                for pos in to_main_pos(w.pos).split("+")
            )
            and w.lemma != "UNKNOWN"
            and bool(w.lemma)  # not empty
            and not any(c.isupper() for c in w.lemma)
        ),
        sort=lambda x: f"{x[0].lemma}{x[0].pos}",
    )
    TokenFilter(out / "unknown_lemmata_capital.txt", corpus).filter(
        lambda w: (
            any(lemma not in lemmata for lemma in re.split(r"[|+]", w.lemma))
            and not any(
                pos in {"PC", "NOU-P", "RES", "NUM"}
                for pos in to_main_pos(w.pos).split("+")
            )
            and w.lemma != "UNKNOWN"
            and bool(w.lemma)  # not empty
            and any(c.isupper() for c in w.lemma)
        ),
        sort=lambda x: f"{x[0].lemma}{x[0].pos}",
    )
    TokenFilter(out / "unknown_lemmata_by_pos.txt", corpus).filter(
        lambda w: (
            any(
                lemma not in pos_to_lemmata.get(pos, set())
                for lemma, pos in zip(
                    re.split(r"[|+]", w.lemma),
                    re.split(r"[|+]", to_main_pos(w.pos)),
                    strict=True,
                )
            )
            and all(lemma in lemmata for lemma in re.split(r"[|+]", w.lemma))
            and not any(
                pos in {"PC", "NOU-P", "RES", "NUM"}
                for pos in to_main_pos(w.pos).split("+")
            )
            and w.lemma != "UNKNOWN"
            and bool(w.lemma)  # not empty
        ),
        sort=lambda x: f"{x[0].lemma}{x[0].pos}",
    )


def largest_diff_token_lemma(corpus: TsvCorpus, out: Path) -> None:
    TokenFilter(out / "largest_diff_token_lemma.txt", corpus).filter(
        lambda w: (
            abs(len(w.group_token) - len(w.lemma)) >= 5
            and all(p not in w.pos for p in ("NUM", "RES"))
            and "WF" not in w.pos
            and "+" not in w.pos
            and w.lemma
            and w.lemma != "UNKNOWN"
        ),
        comment=lambda w: str(abs(len(w.group_token) - len(w.lemma))),
        sort=lambda w: -abs(len(w[0].group_token) - len(w[0].lemma)),
    )


def sus_abbr(corpus: TsvCorpus, out: Path) -> None:
    root = out / "abbr"
    root.mkdir(parents=True, exist_ok=True)
    should_be_abbr(corpus, root)
    long_abbreviations(corpus, root)


def long_abbreviations(corpus: TsvCorpus, root: Path) -> None:
    """Suspicious long abbreviations."""
    TokenFilter(root / "long_abbreviations.txt", corpus).filter(
        lambda w: (
            "WF=abbr" in w.pos
            and abs(len(w.group_token) - len(w.lemma)) <= 2
            and len(w.group_token) > 5
            and "." not in w.group_token
        ),
        sort=lambda w: f"{w[0].lemma}{w[0].group}{w[0].token}",
        uniq=True,
        group=True,
    )


def should_be_abbr(corpus: TsvCorpus, root: Path) -> None:
    """Checks for tokens that should be abbreviations."""
    # Gather all tokens with pos containing WF=abbr. Disregard + and |
    abbr_tokens: dict[str, set[tuple(str, str)]] = defaultdict(set)
    for w in corpus.words:
        if "WF=abbr" in w.pos and "+" not in w.pos and "|" not in w.pos:
            abbr_tokens[to_main_pos(w.pos)].add((w.group_token.lower(), w.lemma))
    TokenFilter(root / "should_be_abbr.txt", corpus).filter(
        lambda w: (
            (
                (
                    (w.group_token.lower() + ".", w.lemma)
                    in abbr_tokens.get(to_main_pos(w.pos), set())
                )
                or (
                    (w.group_token.lower().removesuffix("."), w.lemma)
                    in abbr_tokens.get(to_main_pos(w.pos), set())
                )
            )
            and "WF=abbr" not in w.pos
            and "WF=trunc" not in w.pos
            and "type=uncl" not in w.pos
            and "+" not in w.pos
            and "|" not in w.pos
            # exceptions for de-PD and te-ADP
            and not (to_main_pos(w.pos) == "PD" and w.lemma == "de")
            and not (to_main_pos(w.pos) == "ADP" and w.lemma == "te")
        ),
        uniq=True,
        sort=lambda w: w[0].lemma,
    )
