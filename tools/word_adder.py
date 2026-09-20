#!/usr/bin/env python3
"""Add or update one Huuda pronunciation mapping."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


def update_json_file(filename: Path, original_word: str, replacement_word: str) -> None:
    try:
        data = json.loads(filename.read_text(encoding="utf-8")) if filename.exists() else {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {filename}: {exc}") from exc

    if not original_word:
        raise SystemExit("Refusing to add an empty replacement key.")

    data[original_word] = {
        "replacement": replacement_word,
        "case_insensitive": True,
        "global": True,
    }

    filename.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=filename.name + ".", dir=filename.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_name, filename)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", nargs="?")
    parser.add_argument("replacement", nargs="?")
    parser.add_argument("--file", type=Path, default=Path(__file__).resolve().parents[1] / "wordreplacement.json")
    args = parser.parse_args()

    original = args.original if args.original is not None else input("Original text: ")
    replacement = args.replacement if args.replacement is not None else input("Replacement: ")
    update_json_file(args.file, original, replacement)
    print(f"Updated {args.file}: {original!r} -> {replacement!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
