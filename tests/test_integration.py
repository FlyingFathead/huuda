from __future__ import annotations

import os
from pathlib import Path
import textwrap
import wave

from huuda_tts.cli import main


def test_fake_festival_end_to_end(tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    text2wave = fake_bin / "text2wave"
    text2wave.write_text(
        textwrap.dedent(
            r'''#!/usr/bin/env python3
import argparse
from array import array
import sys
import wave

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-o')
parser.add_argument('-eval')
args = parser.parse_args()
text = sys.stdin.buffer.read()
assert text.strip()
samples = array('h', [0, 4000, -4000, 2000, -2000] * 100)
with wave.open(args.o, 'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(22050)
    wav.writeframes(samples.tobytes())
'''
        ),
        encoding="utf-8",
    )
    text2wave.chmod(0o755)
    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ.get("PATH", ""))

    output = tmp_path / "spoken.wav"
    assert main(["--quiet", "--no-play", "--output", str(output), "Tämä on testi."]) == 0
    assert output.stat().st_size > 44
    with wave.open(str(output), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() > 0


def test_fake_festival_mp3_export(tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    text2wave = fake_bin / "text2wave"
    text2wave.write_text(
        textwrap.dedent(
            r'''#!/usr/bin/env python3
import argparse
from array import array
import sys
import wave

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-o')
parser.add_argument('-eval')
args = parser.parse_args()
assert sys.stdin.buffer.read().strip()
samples = array('h', [0, 4000, -4000, 2000, -2000] * 100)
with wave.open(args.o, 'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(22050)
    wav.writeframes(samples.tobytes())
'''
        ),
        encoding="utf-8",
    )
    text2wave.chmod(0o755)

    # This fake encoder proves that Huuda selects FFmpeg for compressed output
    # and passes a complete WAV as the input. It copies the bytes rather than
    # performing a real MP3 encode so the test has no external dependency.
    ffmpeg = fake_bin / "ffmpeg"
    ffmpeg.write_text(
        textwrap.dedent(
            r'''#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

args = sys.argv[1:]
source = Path(args[args.index('-i') + 1])
destination = Path(args[-1])
assert source.suffix == '.wav'
assert source.stat().st_size > 44
shutil.copyfile(source, destination)
'''
        ),
        encoding="utf-8",
    )
    ffmpeg.chmod(0o755)

    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ.get("PATH", ""))

    output = tmp_path / "spoken.mp3"
    assert main([
        "--quiet",
        "--no-play",
        "--output",
        str(output),
        "--bitrate",
        "160k",
        "Tämä on MP3-testi.",
    ]) == 0
    assert output.stat().st_size > 44
