from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import HuudaError


@dataclass(slots=True)
class ReplacementRule:
    source: str
    replacement: str
    case_insensitive: bool
    probe: str


@dataclass(slots=True)
class ReplacementStats:
    loaded: int = 0
    skipped: int = 0
    matched_rules: int = 0
    replacements: int = 0


class ReplacementTable:
    """Ordered literal replacement table preserving Huuda's legacy semantics.

    Rules are still processed longest-first and may cascade exactly as before.
    The speed-up comes from a cheap literal membership test that skips regex
    work for rules that cannot be present in the current text.
    """

    def __init__(self, rules: list[ReplacementRule], *, skipped: int = 0) -> None:
        self.rules = rules
        self.skipped = skipped

    @classmethod
    def load(cls, path: Path) -> "ReplacementTable":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise HuudaError(f"replacement file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise HuudaError(f"invalid replacement JSON in {path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise HuudaError(f"replacement file must contain a JSON object: {path}")

        rules: list[ReplacementRule] = []
        skipped = 0
        for source in sorted(raw, key=len, reverse=True):
            info = raw[source]
            if not source:
                skipped += 1
                continue
            if not isinstance(info, dict) or not isinstance(info.get("replacement"), str):
                skipped += 1
                continue

            case_insensitive = bool(info.get("case_insensitive", False))
            rules.append(
                ReplacementRule(
                    source=source,
                    replacement=info["replacement"],
                    case_insensitive=case_insensitive,
                    probe=source.casefold() if case_insensitive else source,
                )
            )
        return cls(rules, skipped=skipped)

    def apply(self, text: str, *, debug: bool = False) -> tuple[str, ReplacementStats]:
        stats = ReplacementStats(loaded=len(self.rules), skipped=self.skipped)
        folded = text.casefold()

        for rule in self.rules:
            haystack = folded if rule.case_insensitive else text
            if rule.probe not in haystack:
                continue

            replaced, count = re.subn(
                re.escape(rule.source),
                rule.replacement,
                text,
                flags=re.IGNORECASE if rule.case_insensitive else 0,
            )
            if not count:
                continue

            text = replaced
            folded = text.casefold()
            stats.matched_rules += 1
            stats.replacements += count
            if debug:
                print(f"[huuda] replacement: {rule.source!r} -> {rule.replacement!r} ({count}x)")

        return text, stats
