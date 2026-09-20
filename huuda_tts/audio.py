from __future__ import annotations

import math
import os
import shutil
import sys
import tempfile
import time
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

from .errors import CommandFailed, CommandTimedOut, DependencyError, HuudaError
from .process import ProcessRunner


@dataclass(frozen=True, slots=True)
class PlayerSpec:
    name: str
    command: tuple[str, ...]


PLAYER_CANDIDATES: tuple[PlayerSpec, ...] = (
    PlayerSpec("pw-play", ("pw-play",)),
    PlayerSpec("paplay", ("paplay",)),
    PlayerSpec("aplay", ("aplay", "-q")),
    PlayerSpec("play", ("play", "-q")),
    PlayerSpec("ffplay", ("ffplay", "-nodisp", "-autoexit", "-loglevel", "error")),
    PlayerSpec("afplay", ("afplay",)),
)

# WAV is handled natively. The compressed formats are exported through FFmpeg.
OUTPUT_FORMATS: dict[str, str] = {
    ".wav": "wav",
    ".wave": "wav",
    ".mp3": "mp3",
    ".flac": "flac",
    ".ogg": "ogg",
    ".oga": "ogg",
    ".opus": "opus",
    ".m4a": "m4a",
}
BITRATE_OUTPUT_FORMATS = frozenset({"mp3", "opus", "m4a"})


def available_players() -> list[PlayerSpec]:
    return [spec for spec in PLAYER_CANDIDATES if shutil.which(spec.command[0])]


def choose_player(requested: str) -> PlayerSpec | None:
    if requested == "none":
        return None
    if requested == "auto":
        players = available_players()
        if not players:
            raise DependencyError("no supported audio player found; use --no-play or install pipewire-bin")
        return players[0]

    for spec in PLAYER_CANDIDATES:
        if spec.name == requested:
            if not shutil.which(spec.command[0]):
                raise DependencyError(f"requested audio player is not installed: {requested}")
            return spec
    raise HuudaError(f"unknown audio player: {requested}")


def output_format_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        return OUTPUT_FORMATS[suffix]
    except KeyError as exc:
        supported = ", ".join(sorted(OUTPUT_FORMATS))
        if not suffix:
            raise HuudaError(
                f"output file has no extension; use one of: {supported}"
            ) from exc
        raise HuudaError(
            f"unsupported output extension {suffix!r}; use one of: {supported}"
        ) from exc


def wav_duration(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            return wav.getnframes() / rate if rate else None
    except (wave.Error, OSError):
        return None


def _normalize_pcm16(source: Path, destination: Path, *, target_db: float) -> float:
    """Peak-normalize a 16-bit PCM WAV in two bounded-memory passes."""
    started = time.monotonic()
    chunk_frames = 65536

    try:
        with wave.open(str(source), "rb") as src:
            params = src.getparams()
            if params.comptype != "NONE" or params.sampwidth != 2:
                raise ValueError(
                    f"native normalizer supports 16-bit PCM WAV, got "
                    f"{params.sampwidth * 8}-bit {params.comptype}"
                )

            peak = 0
            while True:
                raw = src.readframes(chunk_frames)
                if not raw:
                    break
                samples = array("h")
                samples.frombytes(raw)
                if sys.byteorder != "little":
                    samples.byteswap()
                if samples:
                    local_peak = max(abs(sample) for sample in samples)
                    peak = max(peak, local_peak)
    except (wave.Error, OSError) as exc:
        raise ValueError(f"unable to read PCM WAV: {exc}") from exc

    # Silence needs no gain calculation but is still copied through wave so the
    # output is a clean, complete WAV.
    target_peak = int(32767 * math.pow(10.0, target_db / 20.0))
    gain = (target_peak / peak) if peak else 1.0

    try:
        with wave.open(str(source), "rb") as src, wave.open(str(destination), "wb") as dst:
            dst.setparams(src.getparams())
            while True:
                raw = src.readframes(chunk_frames)
                if not raw:
                    break
                if peak:
                    samples = array("h")
                    samples.frombytes(raw)
                    if sys.byteorder != "little":
                        samples.byteswap()
                    for i, sample in enumerate(samples):
                        scaled = int(round(sample * gain))
                        samples[i] = max(-32768, min(32767, scaled))
                    if sys.byteorder != "little":
                        samples.byteswap()
                    raw = samples.tobytes()
                dst.writeframesraw(raw)
    except (wave.Error, OSError) as exc:
        raise ValueError(f"unable to write normalized PCM WAV: {exc}") from exc

    return time.monotonic() - started


def _normalize_sox(
    source: Path,
    destination: Path,
    *,
    runner: ProcessRunner,
    timeout: float,
    target_db: float,
) -> float:
    sox = shutil.which("sox")
    if not sox:
        raise DependencyError("sox was not found")
    result = runner.run(
        [sox, str(source), str(destination), "gain", "-n", f"{target_db:g}"],
        stage="SoX normalization",
        timeout=timeout,
    )
    if not destination.exists() or destination.stat().st_size == 0:
        raise HuudaError("SoX returned success but produced no audio")
    return result.elapsed


def normalize_audio(
    source: Path,
    destination: Path,
    *,
    runner: ProcessRunner,
    timeout: float,
    blast: bool = False,
    backend: str = "auto",
) -> tuple[str, float]:
    target_db = -0.1 if blast else -1.0

    if backend in ("auto", "python"):
        try:
            return "python", _normalize_pcm16(source, destination, target_db=target_db)
        except ValueError as exc:
            if backend == "python":
                raise HuudaError(str(exc)) from exc

    if backend in ("auto", "sox"):
        return "sox", _normalize_sox(
            source, destination, runner=runner, timeout=timeout, target_db=target_db
        )

    raise HuudaError(f"unknown normalizer backend: {backend}")


def export_audio(
    source_wav: Path,
    destination: Path,
    *,
    runner: ProcessRunner,
    timeout: float,
    bitrate: str = "192k",
) -> tuple[str, float]:
    """Write the final audio file, inferring format from the destination suffix.

    WAV is copied natively. MP3/FLAC/OGG/Opus/M4A are encoded with FFmpeg.
    The destination is replaced atomically only after a complete export.
    """
    fmt = output_format_for_path(destination)
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Keep the requested extension on the temporary file so FFmpeg can infer
    # the output container/codec normally.
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.huuda-",
        suffix=destination.suffix,
        dir=destination.parent,
    )
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        started = time.monotonic()
        if fmt == "wav":
            shutil.copyfile(source_wav, temp_path)
            elapsed = time.monotonic() - started
        else:
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise DependencyError(
                    f"writing {fmt.upper()} output requires FFmpeg; "
                    "install ffmpeg or use a .wav output file"
                )

            args = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-i",
                str(source_wav),
                "-vn",
            ]
            if fmt in BITRATE_OUTPUT_FORMATS:
                args.extend(["-b:a", bitrate])
            elif fmt == "ogg":
                # Vorbis quality mode behaves sensibly across Festival-style
                # low-rate mono WAVs where a fixed 192k bitrate may be invalid.
                args.extend(["-q:a", "5"])
            args.append(str(temp_path))

            result = runner.run(
                args,
                stage=f"{fmt.upper()} export",
                timeout=timeout,
            )
            elapsed = result.elapsed

        if not temp_path.exists() or temp_path.stat().st_size == 0:
            raise HuudaError(f"{fmt.upper()} export produced no audio")

        os.replace(temp_path, destination)
        return fmt, elapsed
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _run_player(
    spec: PlayerSpec,
    path: Path,
    *,
    runner: ProcessRunner,
    timeout: float,
) -> float:
    binary = shutil.which(spec.command[0])
    if not binary:
        raise DependencyError(f"audio player is not installed: {spec.name}")
    args = [binary, *spec.command[1:], str(path)]
    result = runner.run(args, stage=f"audio playback ({spec.name})", timeout=timeout)
    return result.elapsed


def play_audio(
    path: Path,
    *,
    runner: ProcessRunner,
    player: str,
    timeout: float | None = None,
) -> tuple[str, float]:
    if player == "none":
        return "none", 0.0

    if timeout is None:
        duration = wav_duration(path)
        timeout = max(10.0, (duration * 1.25 + 5.0) if duration is not None else 300.0)

    if player != "auto":
        spec = choose_player(player)
        if spec is None:
            return "none", 0.0
        return spec.name, _run_player(spec, path, runner=runner, timeout=timeout)

    players = available_players()
    if not players:
        raise DependencyError("no supported audio player found; use --no-play or install pipewire-bin")

    failures: list[str] = []
    for spec in players:
        try:
            return spec.name, _run_player(spec, path, runner=runner, timeout=timeout)
        except (CommandFailed, CommandTimedOut, DependencyError) as exc:
            failures.append(f"{spec.name}: {exc}")

    raise HuudaError("all available audio players failed: " + "; ".join(failures))
