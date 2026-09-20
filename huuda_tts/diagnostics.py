from __future__ import annotations

import importlib.util
import platform
import shutil
import tempfile
from pathlib import Path

from .audio import available_players
from .process import ProcessRunner
from .replacements import ReplacementTable
from .synthesis import DEFAULT_FESTIVAL_VOICE, FestivalEngine


def dependency_report(replacement_file: Path) -> list[str]:
    lines = [
        "Huuda diagnostics",
        f"Python: {platform.python_version()} ({platform.system()} {platform.release()})",
        f"text2wave: {shutil.which('text2wave') or 'NOT FOUND'}",
        f"sox (optional normalization fallback): {shutil.which('sox') or 'NOT FOUND'}",
        f"ffmpeg (optional compressed output): {shutil.which('ffmpeg') or 'NOT FOUND'}",
    ]

    players = available_players()
    lines.append("players: " + (", ".join(p.name for p in players) if players else "NONE FOUND"))
    lines.append("Piper module: " + ("available" if importlib.util.find_spec("piper") else "not installed (optional)"))

    try:
        table = ReplacementTable.load(replacement_file)
        lines.append(
            f"replacement table: {replacement_file} ({len(table.rules)} valid rules, {table.skipped} skipped)"
        )
    except Exception as exc:  # diagnostics should report, not explode
        lines.append(f"replacement table: ERROR: {exc}")

    return lines


def festival_smoke_test(*, timeout: float, voice: str = DEFAULT_FESTIVAL_VOICE) -> str:
    if not shutil.which("text2wave"):
        return "Festival smoke test: skipped (text2wave not found)"

    runner = ProcessRunner()
    engine = FestivalEngine(runner)
    try:
        with tempfile.TemporaryDirectory(prefix="huuda-check-") as tmp:
            out = Path(tmp) / "check.wav"
            result = engine.synthesize("Huuda testi.", out, voice=voice, timeout=timeout)
            return f"Festival smoke test: OK ({out.stat().st_size} bytes, {result.elapsed:.2f}s)"
    except Exception as exc:
        return f"Festival smoke test: FAILED: {exc}"
