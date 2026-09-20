# Huuda

**Huuda v0.1.1** is a local command-line speech synthesizer built around Finnish speech engines and a deliberately hand-tuned **Finglish** pronunciation lexicon.

The original Huuda was a compact 2023 Python wrapper around Festival/Festvox Suopuhe, SoX and `play`. v0.1.0 keeps that character but replaces the fragile synchronous glue with bounded subprocess management, diagnostics, selectable playback backends, packaging, tests and an optional modern neural TTS backend.

## What Huuda does

- Finnish speech with Festival + the Suopuhe voices.
- Finglish mode that coerces English text into Finnish-ish pronunciation using the curated `wordreplacement.json` table.
- Optional Piper neural TTS backend.
- Audio-file output and/or immediate playback: WAV natively, plus MP3/FLAC/OGG/Opus/M4A through FFmpeg.
- PipeWire-native playback where available.
- Bounded subprocesses: synthesis/processing cannot silently hang forever.
- Ctrl-C cleanup of active child process groups.
- Dependency and synthesis diagnostics with `--check`.

## Install on Debian / Ubuntu

For the classic Huuda/Suopuhe path:

```bash
sudo apt update
sudo apt install festival festvox-suopuhe-lj festvox-suopuhe-mv pipewire-bin

# Optional: needed for MP3/FLAC/OGG/Opus/M4A output
sudo apt install ffmpeg
```

`pw-play` from `pipewire-bin` is preferred for playback. Huuda will automatically fall back to `paplay`, `aplay`, SoX `play`, `ffplay`, or `afplay` if available. SoX itself is optional in v0.1.0 because ordinary 16-bit PCM WAV normalization is built into Huuda. FFmpeg is optional and is only required when writing compressed output such as MP3, FLAC, OGG, Opus, or M4A.

Install Huuda itself from a checkout into a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/huuda --version
```

For an app-style global command, `pipx install .` is also a good fit.

Or just keep using it directly:

```bash
python3 huuda.py --text "Tämä on testi."
```

## Quick usage

```bash
# Installed console command
huuda "Tämä on testi."

# Historical invocation still works
python3 huuda.py --text "Tämä on testi."

# Finglish
huuda --finglish "It's very nice here."

# Read a UTF-8 text file
huuda --finglish --file speech.txt

# Save WAV and do not play it
huuda --output speech.wav --no-play "Tämä tallennetaan."

# Write MP3 (format is inferred from the filename extension)
huuda -o speech.mp3 --no-play "Tämä tallennetaan MP3:ksi."

# Pick the bitrate for MP3/Opus/M4A
huuda -o speech.mp3 --bitrate 256k --no-play "Kovempi bitrate."

# Lossless compressed output
huuda -o speech.flac --no-play "FLAC-versio."

# Skip peak normalization entirely
huuda --no-normalize "Raaka syntetisaattorin WAV."

# Force a playback backend
huuda --player pw-play "PipeWire suoraan."
```

## Audio-file output

`-o/--output` writes the final post-processed audio to disk. The format is inferred from the filename extension:

```bash
huuda -o voice.wav  --no-play "WAV"
huuda -o voice.mp3  --no-play "MP3"
huuda -o voice.flac --no-play "FLAC"
huuda -o voice.ogg  --no-play "Ogg Vorbis"
huuda -o voice.opus --no-play "Opus"
huuda -o voice.m4a  --no-play "M4A/AAC"
```

WAV is written without an external encoder. The compressed formats require `ffmpeg`. MP3, Opus and M4A default to `192k` and can be changed with `--bitrate`; OGG/Vorbis uses quality mode because fixed high bitrates can be invalid for the low-rate mono WAV produced by classic Festival voices.

Specifying `--output` does **not** disable playback. Add `--no-play` when you only want the file. Playback always uses Huuda's internal WAV master, so saving an MP3 does not make the playback path depend on MP3 decoding.

## If Huuda hangs or audio breaks

v0.1.0 has a diagnostics path specifically for this:

```bash
huuda --check
```

It reports the active Python version, `text2wave`, SoX, FFmpeg, discovered playback backends, the optional Piper module, the replacement table, and runs a short Festival synthesis test with a hard timeout.

For stage timings and Finglish rule hits:

```bash
huuda --debug --finglish "The computer is extremely sophisticated."
```

Every external stage is bounded by `--timeout` (30 seconds by default). Playback uses a WAV-duration-derived timeout unless `--playback-timeout` is supplied. Normal 16-bit PCM peak normalization is performed inside Huuda; `--normalizer sox` remains available as a fallback/compatibility path. Output is written atomically: Huuda only replaces the requested file after the complete export succeeds.

```bash
huuda --timeout 10 --playback-timeout 20 "Testi."
```

Ctrl-C is handled by Huuda itself. On POSIX systems the backend is started in its own process session; Huuda terminates that process group before exiting.

## Festival / Suopuhe engine

Festival remains the default because the old Suopuhe diphone voice is part of Huuda's sound rather than merely a dependency.

Default voice:

```text
(voice_hy_fi_mv_diphone)
```

Override it with:

```bash
huuda --voice '(voice_hy_fi_lj_diphone)' "Testi."
```

Festival input retains Huuda's historical Latin-1 behavior. Unsupported characters are dropped only at the Festival boundary; the rest of Huuda handles normal Python Unicode text.

## Optional Piper engine

Piper is **not required** for classic Huuda. It is an additional engine.

Install it into the same Python environment:

```bash
python3 -m pip install 'piper-tts>=1.4'
python3 -m piper.download_voices fi_FI-harri-medium
```

Then:

```bash
huuda --engine piper --piper-model fi_FI-harri-medium "Tämä on Piper."
```

A local `.onnx` model path can also be passed to `--piper-model`.

Huuda deliberately asks Piper to create a WAV and performs playback itself instead of delegating playback to Piper. This keeps one cancellation/playback policy for every synthesis engine.

## Finglish replacement system

Finglish mode is not generic transliteration. `wordreplacement.json` is a large curated pronunciation/coercion table designed around how the Finnish voice actually sounds.

v0.1.0 preserves the old replacement behavior:

1. longer keys are processed before shorter keys;
2. case-insensitive rules remain case-insensitive;
3. replacements remain sequential and can cascade into later rules.

The implementation now performs a cheap literal membership test before invoking regex. This avoids running thousands of unnecessary regex substitutions while retaining the old result.

Use another table with:

```bash
huuda --finglish --replacement-file my_words.json "Text here."
```

Add/update an entry:

```bash
python3 tools/word_adder.py "pipeline" "páípláín"
```

## Main options

```text
--finglish / --english / --eng / --en / -e
--engine festival|piper
--voice FESTIVAL_EXPRESSION
--piper-model MODEL_OR_PATH
--cuda
--file / -f FILE
--text / -t TEXT
--output / -o FILE.(wav|mp3|flac|ogg|oga|opus|m4a)
--bitrate RATE
--no-play
--player auto|pw-play|paplay|aplay|play|ffplay|afplay|none
--no-normalize
--normalizer auto|python|sox
--blast
--timeout SECONDS
--playback-timeout SECONDS
--check
--dry-run
--debug
--quiet
--version
```

## Development

```bash
python3 -m pip install -e '.[dev]'
pytest
```

## License / ethos

Huuda has historically been published under a "go for it" ethos, in the spirit of The Unlicense / WTFPL: use it, modify it, make it yell strange things.
