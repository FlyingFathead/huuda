#!/usr/bin/env python3
"""Compatibility entry point for Huuda.

`python3 huuda.py ...` remains supported; installed users can simply run `huuda`.
"""

from huuda_tts.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
