#!/usr/bin/env python3

"""Normalize TEI files to correct TEI-P5."""

import sys
import xml.etree.ElementTree as ET
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.normalizer import ns
from scripts.normalizer.attributes import normalize_attributes
from scripts.normalizer.header import normalize_tei_header
from scripts.normalizer.notes import place_notes
from scripts.normalizer.structure import fix_structural_issues
from scripts.normalizer.tags import remove_invalid_tags
from scripts.normalizer.tokens import normalize_tokens


def normalize_root(root: ET.Element) -> None:
    """
    Normalize root to <TEI>.

    Raises:
        ValueError: root was neither TEI nor TEI.2.
    """
    if root.tag not in {f"{ns['tei']}TEI", "TEI.2"}:
        raise ValueError(f"Unexpected root tag {root.tag}")

    if root.tag == "TEI.2":
        root.tag = f"{ns['tei']}TEI"


def normalize(file: Path) -> None:
    """Normalize the file to valid tei-p5."""
    # Remove weird characters
    file_text = file.read_text(encoding="utf-8")
    file_text = (
        file_text
        .replace("\u2011", "-")  # non-breaking hyphen to regular hyphen
        .replace("\u00ad", "")  # soft hyphens
        .replace("\u202f", "")  # narrow no-break space
    )
    file.write_text(file_text, encoding="utf-8")

    tree: ET.ElementTree = ET.parse(file)
    root: ET.Element = tree.getroot()

    # normalize namespace issues by rewriting and reparsing before any other fixes
    normalize_root(root)
    write(tree, file)

    tree: ET.ElementTree = ET.parse(file)
    root: ET.Element = tree.getroot()

    # The order is significant.
    # E.g. normalize_attributes() removes all @lemmaRef's.
    # Whereas fix_structural_issues() adds valid @lemmaRef's to `<cit>`'s.
    normalize_attributes(root)
    normalize_tei_header(root)
    fix_structural_issues(root)
    normalize_tokens(root)
    place_notes(root)
    remove_invalid_tags(root)

    write(tree, file)


def write(tree: ET.ElementTree, file: Path) -> None:
    """Pretty print XML to file."""
    ET.indent(tree, space="  ")
    tree.write(file, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Lancelot TEI XML validator",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-r", action="store_true", help="Recursive")
    parser.add_argument("-m", type=int, default=4, help="Multithreads")
    parser.add_argument("input", type=Path, help="xml file or dir")
    args = parser.parse_args()

    if args.input.is_file() and args.r:
        raise ValueError("Cannot use -r with a single file input")

    if args.input.is_file():
        normalize(args.input)
        print(f"Normalized {args.input}")
        sys.exit(0)

    if args.input.is_dir():
        files = list(args.input.rglob("*.xml") if args.r else args.input.glob("*.xml"))

        # if tqdm is available, use it
        try:
            from tqdm import tqdm
        except ImportError:
            tqdm = lambda x, **_: x  # fallback: identity

        with ThreadPoolExecutor(max_workers=args.m) as executor:
            list(
                tqdm(
                    executor.map(normalize, files),
                    total=len(files),
                ),
            )
        print(f"Normalized {len(files)} files")
