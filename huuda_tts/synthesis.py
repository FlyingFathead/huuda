from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import DependencyError, HuudaError
from .process import ProcessRunner


DEFAULT_FESTIVAL_VOICE = "(voice_hy_fi_mv_diphone)"
DEFAULT_PIPER_MODEL = "fi_FI-harri-medium"


@dataclass(slots=True)
class SynthesisResult:
    engine: str
    output: Path
    elapsed: float


class FestivalEngine:
    name = "festival"

    def __init__(self, runner: ProcessRunner) -> None:
        self.runner = runner

    @staticmethod
    def available() -> bool:
        return shutil.which("text2wave") is not None

    def synthesize(self, text: str, output: Path, *, voice: str, timeout: float) -> SynthesisResult:
        binary = shutil.which("text2wave")
        if not binary:
            raise DependencyError("text2wave was not found (install Festival/Festvox Suopuhe)")

        # Suopuhe/Festival expects the historical Latin-1 input used by Huuda.
        # Unsupported Unicode is intentionally dropped for compatibility.
        encoded = text.encode("latin-1", errors="ignore")
        if not encoded.strip():
            raise HuudaError("text became empty after Festival Latin-1 conversion")

        result = self.runner.run(
            [binary, "-o", str(output), "-eval", voice],
            stage="Festival/text2wave synthesis",
            input_data=encoded + b"\n",
            timeout=timeout,
        )
        if not output.exists() or output.stat().st_size == 0:
            raise HuudaError("Festival/text2wave returned success but produced no audio")
        return SynthesisResult(self.name, output, result.elapsed)


class PiperEngine:
    name = "piper"

    def __init__(self, runner: ProcessRunner) -> None:
        self.runner = runner

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("piper") is not None

    def synthesize(
        self,
        text: str,
        output: Path,
        *,
        model: str,
        timeout: float,
        cuda: bool = False,
    ) -> SynthesisResult:
        if not self.available():
            raise DependencyError(
                "Piper is not installed in this Python environment (optional: pip install piper-tts)"
            )

        args = [sys.executable, "-m", "piper", "--model", model, "--output-file", str(output)]
        if cuda:
            args.append("--cuda")

        result = self.runner.run(
            args,
            stage="Piper synthesis",
            input_data=(text.rstrip() + "\n").encode("utf-8"),
            timeout=timeout,
        )
        if not output.exists() or output.stat().st_size == 0:
            raise HuudaError("Piper returned success but produced no audio")
        return SynthesisResult(self.name, output, result.elapsed)
