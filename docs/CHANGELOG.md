# Changelog

## Huuda 0.1.1 - 2026-09-20

Small Finglish lexicon update.

- Added additional hand-tuned pronunciation entries.
- No synthesis, playback, export, or CLI behavior changes.

## Huuda 0.1.0 - 2026-09-20

First packaged release and a substantial modernization of the original 2023 script.

### Reliability

- Added bounded subprocess execution for synthesis, SoX processing, and playback.
- External commands run in isolated process groups on POSIX systems.
- Ctrl-C now terminates the active backend process group instead of waiting indefinitely for it.
- Timeouts terminate a stuck backend and return a clear stage-specific error.
- Temporary audio is held in a `TemporaryDirectory` and cleaned automatically.
- Removed the temporary text file: Festival `text2wave` now receives input on stdin.
- Added `--check` diagnostics and a bounded Festival synthesis smoke test.

### Audio

- Added automatic playback backend selection: `pw-play`, `paplay`, `aplay`, `play`, `ffplay`, then `afplay`.
- PipeWire-native `pw-play` is preferred where available.
- Added `--player`, `--no-play`, `--output`, and `--playback-timeout`.
- `--output/-o` now infers the requested audio format from the filename: WAV is native; MP3, FLAC, OGG/Vorbis, Opus and M4A use optional FFmpeg.
- Added `--bitrate` for MP3/Opus/M4A output; OGG uses Vorbis quality mode.
- Output files are committed atomically only after a complete export succeeds.
- Added built-in two-pass 16-bit PCM peak normalization, avoiding a subprocess for the normal path.
- Retained SoX as an optional/fallback normalizer with explicit `gain -n` peak targets.
- `--blast` now has defined behavior instead of combining an extreme input gain with normalization.

### Synthesis engines

- Festival/Suopuhe remains the default and retains the historical Latin-1 behavior.
- Added an optional Piper backend with `--engine piper` and `--piper-model`.
- Default optional Piper model name is `fi_FI-harri-medium`.

### Finglish lexicon

- Preserved longest-first sequential/cascading replacement semantics.
- Added a literal prefilter before regex replacement, reducing typical replacement time by orders of magnitude.
- Removed the invalid empty-string replacement key.
- Replacement diagnostics are available with `--debug`.
- Modernized `word_adder.py` with atomic writes and empty-key rejection.

### Packaging and CLI

- Added `pyproject.toml` and a `huuda` console command.
- `python3 huuda.py ...` remains supported as a compatibility entry point.
- Added positional text input, `--version`, `--dry-run`, `--debug`, and `--quiet`.
- Added an initial automated test suite.
