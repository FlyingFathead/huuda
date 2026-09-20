from array import array
from pathlib import Path
import os
import wave

import pytest

from huuda_tts.audio import normalize_audio
from huuda_tts.process import ProcessRunner


def _write_wav(path: Path, peak: int = 4000) -> None:
    samples = array("h", [0, peak, -peak, peak // 2, -(peak // 2)] * 100)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(samples.tobytes())


def _peak(path: Path) -> int:
    with wave.open(str(path), "rb") as wav:
        samples = array("h")
        samples.frombytes(wav.readframes(wav.getnframes()))
    return max(abs(x) for x in samples)


def test_native_normalizer(tmp_path):
    source = tmp_path / "in.wav"
    output = tmp_path / "out.wav"
    _write_wav(source)
    backend, elapsed = normalize_audio(
        source,
        output,
        runner=ProcessRunner(),
        timeout=2,
        backend="python",
    )
    assert backend == "python"
    assert elapsed >= 0
    assert 29000 < _peak(output) < 30000  # -1 dBFS ~= 29203


def test_output_format_for_path():
    from huuda_tts.audio import output_format_for_path

    assert output_format_for_path(Path("speech.wav")) == "wav"
    assert output_format_for_path(Path("speech.MP3")) == "mp3"
    assert output_format_for_path(Path("speech.flac")) == "flac"
    assert output_format_for_path(Path("speech.ogg")) == "ogg"
    assert output_format_for_path(Path("speech.opus")) == "opus"
    assert output_format_for_path(Path("speech.m4a")) == "m4a"


def test_export_wav_natively(tmp_path):
    from huuda_tts.audio import export_audio

    source = tmp_path / "in.wav"
    output = tmp_path / "nested" / "spoken.wav"
    _write_wav(source)

    fmt, elapsed = export_audio(
        source,
        output,
        runner=ProcessRunner(),
        timeout=2,
    )

    assert fmt == "wav"
    assert elapsed >= 0
    assert output.read_bytes() == source.read_bytes()



def test_failed_compressed_export_preserves_existing_destination(tmp_path, monkeypatch):
    from huuda_tts.audio import export_audio
    from huuda_tts.errors import CommandFailed

    source = tmp_path / "in.wav"
    _write_wav(source)
    destination = tmp_path / "spoken.mp3"
    destination.write_bytes(b"previous-good-file")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    ffmpeg = fake_bin / "ffmpeg"
    ffmpeg.write_text(
        "#!/bin/sh\nprintf 'partial' > \"${@: -1}\" 2>/dev/null || true\nexit 1\n",
        encoding="utf-8",
    )
    # POSIX /bin/sh does not support ${@: -1} everywhere, but the command's
    # failure is enough for the atomicity contract: Huuda must not touch the
    # existing destination unless the export succeeds.
    ffmpeg.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ.get("PATH", ""))

    with pytest.raises(CommandFailed):
        export_audio(
            source,
            destination,
            runner=ProcessRunner(),
            timeout=2,
        )

    assert destination.read_bytes() == b"previous-good-file"
