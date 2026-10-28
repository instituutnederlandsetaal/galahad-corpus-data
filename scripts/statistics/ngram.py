from collections import Counter, defaultdict
from pathlib import Path

from scripts.statistics.data import TsvCorpus, TsvWord
from scripts.statistics.token_filter import TokenFilter
from scripts.statistics.util import to_main_pos


class SuspiciousNgrams:
    def __init__(self, corpus: TsvCorpus, out: Path):
        self.corpus: TsvCorpus = corpus
        self.out: Path = out
        self.suspicious_groups: set[str] = SuspiciousNgrams.calculate_groups(corpus)

    @staticmethod
    def calculate_groups(corpus: TsvCorpus) -> set[str]:
        pos_freq: Counter[str] = SuspiciousNgrams.calculate_pos_freq(corpus)
        ngram_counts: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
        for doc in corpus.docs:
            words = list(doc.words)
            for i in range(len(words) - 2):
                # skip if any of the posses is "PC" or "RES"
                posses = {
                    to_main_pos(p)
                    for p in (words[i].pos, words[i + 1].pos, words[i + 2].pos)
                }
                if {"PC", "RES"} & posses:
                    continue
                # count the middle word's POS between the first and third word's POS
                ngram_counts[words[i].pos, words[i + 2].pos][words[i + 1].pos] += 1

        suspicious_groups = set()
        for (pos1, pos3), counter in ngram_counts.items():
            total_count = sum(counter.values())
            for pos2, count in counter.items():
                if (
                    count == 1
                    and total_count > 1000
                    and (
                        pos_freq[pos1] > 100
                        and pos_freq[pos2] > 100
                        and pos_freq[pos3] > 100
                    )
                ):  # threshold for suspiciousness
                    suspicious_groups.add(f"{pos1}{pos2}{pos3}")

        return suspicious_groups

    @staticmethod
    def calculate_pos_freq(corpus: TsvCorpus) -> Counter[str]:
        pos_freq: Counter[str] = Counter()
        for word in corpus.words:
            pos_freq[word.pos] += 1
        return pos_freq

        # # sort by the most common dict key. common defined as the sum of its counter frequencies
        # ngram_counts = dict(
        #     sorted(
        #         ngram_counts.items(),
        #         key=lambda item: sum(item[1].values()),
        #         reverse=True,
        #     ),
        # )

    def is_suspicious(self, w: list[TsvWord]) -> bool:
        w1, w2, w3 = w
        # ignore multi pos for now
        if "+" in w2.pos or "WF=abbr" in w2.pos or "WF=mis" in w2.pos:
            return False
        pos = f"{w1.pos}{w2.pos}{w3.pos}"
        return pos in self.suspicious_groups

    def report(self):
        TokenFilter(self.out, self.corpus).report(self.is_suspicious, ngram=3)


# def ngram(corpus: TsvCorpus, root: Path) -> None:

#     def suspicious_ngram(w: list[TsvWord]):
#         p1, p2, p3 = w
#         if (
#             to_main_pos(p1.pos) == "AA"
#             and to_main_pos(p2.pos) == "AA"
#             and to_main_pos(p3.pos) == "NOU-C"
#         ):
#             return True
#         return False

#     exit()
#     out = root / "ngram_counts.txt"

#     with out.open("w", encoding="utf-8") as f:
#         for posses, counter in ngram_counts.items():
#             for pos2, count in counter.most_common():
#                 pos1, pos3 = posses
#                 f.write(f"{count:>5} {pos1:<40} {pos2:<40} {pos3:<40}\n")
#             f.write("\n\n\n")
