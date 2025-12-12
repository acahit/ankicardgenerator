from __future__ import annotations
"""Small utility to parse pasted tabular text into CSV/TSV files.

This module exposes `parse_text_to_rows` and `write_rows` and also ships a
convenient CLI for quick one-off conversions. It's intended for pasting text
from spreadsheets or aligned text tables and exporting CSV/TSV files for
Anki import or similar workflows.
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable

CANDIDATE_DELIMS = [",", ";", "|"]


def parse_text_to_rows(text: str) -> list[list[str]]:
    """Parse pasted text into a list of rows (list of string cells).

    Detection steps (in order):
    - If there are TAB characters: split on TAB
    - Use csv.Sniffer over common delimiters
    - Fallback: split on two-or-more spaces (aligned table)
    """
    text = text.strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    sample = "\n".join(lines[:20])

    # 1) Excel/Sheets paste: TAB
    if "\t" in sample:
        return [ln.split("\t") for ln in lines]

    # 2) Delimited: try sniffer on common delimiters
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(CANDIDATE_DELIMS))
        reader = csv.reader(lines, dialect)
        return [row for row in reader]
    except Exception:
        pass

    # 3) Fallback: split by 2+ spaces (aligned text tables)
    rows: list[list[str]] = []
    for ln in lines:
        rows.append([cell.strip() for cell in re.split(r"\s{2,}", ln.strip())])
    return rows


def write_rows(rows: Iterable[Iterable[str]], out_path: Path, sep: str = ",") -> None:
    """Write parsed rows to `out_path` using the `sep` delimiter.

    Creates parent directories when necessary. Uses UTF-8 and minimal quoting
    for consistent, portable CSV output.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=sep, quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Convert pasted tabular text into CSV/TSV.")
    p.add_argument("--in", dest="inp", type=Path, default=Path("input.txt"), help="Input file (default: input.txt)")
    p.add_argument("--out", dest="out", type=Path, default=Path("output.csv"), help="Output file (default: output.csv)")
    p.add_argument("--sep", dest="sep", type=str, default=",")
    p.add_argument("--tsv", dest="tsv", action="store_true", help="Write TSV (tabs) instead of CSV")
    p.add_argument("--quiet", dest="quiet", action="store_true", help="Suppress status prints")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = _build_parser().parse_args(argv)

    sep = "\t" if args.tsv else args.sep
    try:
        text = args.inp.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.inp}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error reading input: {exc}", file=sys.stderr)
        return 3

    rows = parse_text_to_rows(text)
    try:
        write_rows(rows, args.out, sep=sep)
    except Exception as exc:
        print(f"Error writing output: {exc}", file=sys.stderr)
        return 4

    if not args.quiet:
        print(f"✅ {len(rows)} rows written -> {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
