"""Data model for TSV files in galahad-corpus-data."""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import override


class Split(StrEnum):
    """Machine learning dataset splits."""

    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


@dataclass
class TsvWord:
    """A single annotated token with lemma, POS and MWE group."""

    token: str
    pos: str
    lemma: str
    group: str
    mwe: list["TsvWord"] = field(default_factory=list)

    @staticmethod
    def load(text: str) -> "TsvWord":
        """Parse a single TSV row into a TsvWord."""
        cols = text.split("\t")
        # TSV column order: token \t pos \t lemma \t group
        return TsvWord(cols[0], cols[1], cols[2], cols[3])

    @override
    def __str__(self) -> str:
        return f"{self.token:<20}\t{self.lemma:<20}\t{self.pos}\t{self.group}"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    @override
    def __hash__(self) -> int:
        return hash((self.token, self.pos, self.lemma, self.group))

    @property
    def group_token(self) -> str:
        """Concatenated token string of the group."""
        return "".join(t.token for t in self.mwe) if self.group else self.token


@dataclass
class TsvSentence:
    """A sentence of TsvWords. Sentences are separated by one blank line."""

    words: list[TsvWord]

    @staticmethod
    def load(text: str) -> "TsvSentence":
        """Parse a TSV sentence block into words."""
        # Words are one per line.
        rows = text.split("\n")
        return TsvSentence([TsvWord.load(r) for r in rows if r.strip()])

    @override
    def __str__(self) -> str:
        return f"          Sentence ({len(self.words)} words)"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Iterator[TsvWord]:
        """Yield words in sentence."""
        return iter(self.words)


@dataclass
class TsvParagraph:
    """A paragraph of TsvSentences: Paragraphs are separated by two blank lines."""

    sents: list[TsvSentence]

    @property
    def words(self) -> Iterator[TsvWord]:
        """
        Yields:
            words in sentences in paragraph.
        """
        for s in self.sents:
            yield from s.words

    @staticmethod
    def load(text: str) -> "TsvParagraph":
        """Parse a TSV paragraph block into sentences."""
        # Sentences are split by one empty line.
        sents = text.split("\n\n")
        return TsvParagraph([TsvSentence.load(s) for s in sents if s.strip()])

    @override
    def __str__(self) -> str:
        return f"        Paragraph ({len(self.sents)} sents)\n{'\n'.join([str(s) for s in self.sents])}"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Iterator[TsvSentence]:
        """Yield sentences in paragraph."""
        return iter(self.sents)


@dataclass
class TsvDocument:
    """A document of TsvParagraphs. Documents are separated by three blank lines."""

    pars: list[TsvParagraph]

    @property
    def sents(self) -> Iterator[TsvSentence]:
        """
        Yields:
            sentences in paragraphs in document.
        """
        for p in self.pars:
            yield from p.sents

    @property
    def words(self) -> Iterator[TsvWord]:
        """
        Yields:
            words in sentences in paragraphs in document.
        """
        for p in self.pars:
            yield from p.words

    @staticmethod
    def load(text: str) -> "TsvDocument":
        """Parse a TSV document block into paragraphs. Create MWE word links."""
        # Paragraphs are split by two empty lines.
        pars = text.split("\n\n\n")
        doc = TsvDocument([TsvParagraph.load(p) for p in pars if p.strip()])
        # Link MWE's on document level, as they may span paragraphs (letters-as-loot).
        TsvDocument._link_mwes(doc)
        return doc

    @staticmethod
    def _link_mwes(doc: "TsvDocument") -> None:
        """Link TsvWord.mwe so every token links to its group."""
        # Collect groups.
        group_map: dict[str, list[TsvWord]] = defaultdict(list)
        for w in doc.words:
            if w.group:
                group_map[w.group].append(w)
        # Link MWEs.
        for group in group_map.values():
            for w in group:
                w.mwe = list(group)

    @override
    def __str__(self) -> str:
        return f"      Document ({len(self.pars)} pars)\n{'\n'.join([str(p) for p in self.pars])}"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Iterator[TsvParagraph]:
        """Yield paragraphs in document."""
        return iter(self.pars)


@dataclass
class TsvFile:
    """
    One `.tsv` file on disk (e.g. `clvn.train.tsv`) representing a single split.
    Contains multiple source documents.
    """

    filename: str
    docs: list[TsvDocument]

    @property
    def name(self) -> str:
        """Dataset name. E.g. `clvn` for `clvn.train.tsv`."""
        return self.filename.split(".")[0]

    @property
    def split(self) -> Split:
        """Train/dev/test split derived from the filename."""
        return Split(self.filename.split(".")[1])

    @property
    def pars(self) -> Iterator[TsvParagraph]:
        """
        Yields:
            paragraphs in documents in file.
        """
        for d in self.docs:
            yield from d.pars

    @property
    def sents(self) -> Iterator[TsvSentence]:
        """
        Yields:
            sentences in paragraphs in documents in file.
        """
        for d in self.docs:
            yield from d.sents

    @property
    def words(self) -> Iterator[TsvWord]:
        """
        Yields:
            words in sentences in paragraphs in documents in file.
        """
        for d in self.docs:
            yield from d.words

    @staticmethod
    def load(f: Path) -> "TsvFile":
        """Parse a `.tsv` file into documents."""
        rows = f.read_text(encoding="utf-8")
        # Docs are split by three empty lines.
        docs = rows.split("\n\n\n\n") if rows else []
        return TsvFile(f.name, [TsvDocument.load(d) for d in docs if d.strip()])

    @override
    def __str__(self) -> str:
        return f"    {self.filename} ({len(self.docs)} docs)\n{'\n'.join([str(d) for d in self.docs])}"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Iterator[TsvDocument]:
        """Yield documents in file."""
        return iter(self.docs)


@dataclass
class TsvDir:
    """One dataset directory containing the three TSV split files."""

    name: str
    train: TsvFile
    test: TsvFile
    dev: TsvFile
    split: str = "total"

    @property
    def splits(self) -> list[TsvFile]:
        """Convenience list of all three split files in [train, test, dev] order."""
        return [self.train, self.test, self.dev]

    @property
    def docs(self) -> Iterator[TsvDocument]:
        """
        Yields:
            every document across all splits.
        """
        for split in self.splits:
            yield from split.docs

    @property
    def pars(self) -> Iterator[TsvParagraph]:
        """
        Yields:
            every paragraph across all splits.
        """
        for split in self.splits:
            yield from split.pars

    @property
    def sents(self) -> Iterator[TsvSentence]:
        """
        Yields:
            every sentence across all splits.
        """
        for split in self.splits:
            yield from split.sents

    @property
    def words(self) -> Iterator[TsvWord]:
        """
        Yields:
            every word across all splits.
        """
        for split in self.splits:
            yield from split.words

    @staticmethod
    def load(folder: Path) -> "TsvDir":
        """
        Parse dataset directory into three split files.
        Files are called [name].train.tsv, [name].test.tsv, [name].dev.tsv.
        """
        train = TsvFile.load(folder / f"{folder.name}.train.tsv")
        test = TsvFile.load(folder / f"{folder.name}.test.tsv")
        dev = TsvFile.load(folder / f"{folder.name}.dev.tsv")
        return TsvDir(folder.name, train, test, dev)

    @override
    def __str__(self) -> str:
        return f"  {self.name}\n{'\n'.join([str(s) for s in self.splits])}"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Iterator[TsvFile]:
        """Yield split files in [train, test, dev] order."""
        return iter(self.splits)


@dataclass
class TsvSplit:
    """A cross-dataset view of a single split (e.g. all train files)."""

    name: str
    files: list[TsvFile]

    @property
    def docs(self) -> Iterator[TsvDocument]:
        """
        Yields:
            every document across all files in this split.
        """
        for f in self.files:
            yield from f.docs

    @property
    def words(self) -> Iterator[TsvWord]:
        """
        Yields:
            every word across all files in this split.
        """
        for f in self.files:
            yield from f.words

    def __iter__(self) -> Iterator[TsvFile]:
        """Yield files in split."""
        return iter(self.files)


@dataclass
class TsvSplits:
    """Container that groups the three cross-dataset split views together."""

    train: TsvSplit
    dev: TsvSplit
    test: TsvSplit
    name: str = "total"

    @property
    def docs(self) -> Iterator[TsvDocument]:
        """
        Yields:
            every document across all three splits.
        """
        for s in self:
            yield from s.docs

    @property
    def words(self) -> Iterator[TsvWord]:
        """
        Yields:
            every word across all three splits.
        """
        for s in self:
            yield from s.words

    def __iter__(self) -> Iterator[TsvSplit]:
        """Yield cross-dataset split views in [train, dev, test] order."""
        return iter([self.train, self.dev, self.test])


@dataclass
class TsvCorpus:
    """TSV corpus with splits, dataset directories, documents, sentences and words."""

    dirs: list[TsvDir]
    name: str = "total"

    @property
    def docs(self) -> Iterator[TsvDocument]:
        """
        Yields:
            every document across all dataset directories.
        """
        for d in self.dirs:
            yield from d.docs

    @property
    def words(self) -> Iterator[TsvWord]:
        """
        Yields:
            every word across all dataset directories.
        """
        for d in self.dirs:
            yield from d.words

    @property
    def sents(self) -> Iterator[TsvSentence]:
        """
        Yields:
            every sentence across all dataset directories.
        """
        for d in self.dirs:
            yield from d.sents

    @property
    def train(self) -> TsvSplit:
        """Cross-dataset view of all training files."""
        return TsvSplit("train", [d.train for d in self.dirs])

    @property
    def dev(self) -> TsvSplit:
        """Cross-dataset view of all development/validation files."""
        return TsvSplit("dev", [d.dev for d in self.dirs])

    @property
    def test(self) -> TsvSplit:
        """Cross-dataset view of all test files."""
        return TsvSplit("test", [d.test for d in self.dirs])

    @property
    def splits(self) -> TsvSplits:
        """Grouped container of the three cross-dataset split views."""
        return TsvSplits(self.train, self.dev, self.test)

    @staticmethod
    def load(folder: Path) -> "TsvCorpus":
        """Load all dataset sub-directories under the folder."""
        return TsvCorpus([
            TsvDir.load(f) for f in sorted(folder.iterdir()) if f.is_dir()
        ])

    @override
    def __str__(self) -> str:
        return f"{self.name}\n{'\n'.join([str(d) for d in self.dirs])}"

    @override
    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Iterator[TsvDir]:
        """Yield dataset directories in corpus."""
        return iter(self.dirs)
