#!/usr/bin/env python3

"""Change the column order from galahad to this repository's format."""

import os
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Lancelot TSV column fixer",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("dir", type=Path, help="Directory containing .tsv files")
    parser.add_argument("-r", action="store_true", help="Recursive")
    args = parser.parse_args()

    files = list(args.dir.rglob("*.tsv") if args.r else args.dir.glob("*.tsv"))
    for file in files:
        os.system(
            f"""awk -F'\\t' -v OFS='\\t' '{{print $2, $4, $3, (NF == 4 ? "" : $NF)}}' {file} | tail -n +2 > {file}.fixed""",
        )
        Path(f"{file}.fixed").replace(file)
        # dos2unix conversion
        os.system(f"dos2unix {file}")
        # awk will create "empty" rows (with only tabs): replace them with empty lines (dont delete!)
        os.system(f"sed -i 's/^[\t]*$//' {file}")

    print(f"Fixed {len(files)} files.")
