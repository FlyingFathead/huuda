import json
import re
from pathlib import Path

from huuda_tts.replacements import ReplacementTable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "wordreplacement.json"


def legacy_replace(text: str) -> str:
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    for source in sorted(raw, key=len, reverse=True):
        if not source:
            continue
        info = raw[source]
        flags = re.IGNORECASE if info.get("case_insensitive") else 0
        text = re.sub(re.escape(source), info["replacement"], text, flags=flags)
    return text


def test_fast_prefilter_preserves_legacy_result():
    text = (
        "Yes sir, I can boogie. The computer is extremely sophisticated, "
        "and your feedback about the pipeline is very useful. "
        "This is a longer context for testing Huuda's Finglish replacement system."
    )
    table = ReplacementTable.load(DATA)
    actual, stats = table.apply(text)
    assert actual == legacy_replace(text)
    assert stats.loaded > 8000


def test_empty_rule_is_not_loaded():
    table = ReplacementTable.load(DATA)
    assert all(rule.source for rule in table.rules)
