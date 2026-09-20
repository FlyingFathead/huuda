#!/usr/bin/env python3
"""Convert Huuda's historical sed-style replacement list to JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SED_RE = re.compile(r'sed -i "s/(.*?)/(.*?)/(gI|g|I)" "\\?\$spk"')


def unescape_string(value: str) -> str:
    return value.replace(r"\,", ",").replace(r"\.", ".")


def parse_sed_to_json(infile: Path, outfile: Path) -> int:
    replacement_dict: dict[str, dict[str, object]] = {}
    ignored = 0

    for line in infile.read_text(encoding="utf-8").splitlines():
        match = SED_RE.fullmatch(line.strip())
        if not match:
            if line.strip():
                ignored += 1
            continue

        original, replacement, flags = match.groups()
        original = unescape_string(original)
        replacement = unescape_string(replacement)
        if not original:
            ignored += 1
            continue

        replacement_dict[original] = {
            "replacement": replacement,
            "case_insensitive": "I" in flags,
            "global": "g" in flags,
        }

    outfile.write_text(
        json.dumps(replacement_dict, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return ignored


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("infile", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    outfile = args.output or args.infile.with_suffix(".json")
    ignored = parse_sed_to_json(args.infile, outfile)
    print(f"Wrote {outfile} ({ignored} non-matching/invalid lines ignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
