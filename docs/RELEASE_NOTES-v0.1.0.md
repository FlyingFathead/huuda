# Huuda v0.1.0

Huuda v0.1.0 is the first packaged release and a substantial modernization of the original 2023 Finnish/Finglish TTS script.

## Highlights

- Festival/Festvox Suopuhe remains the default Huuda voice path.
- Ctrl-C and timeouts now terminate the active backend process group instead of leaving Huuda waiting on a wedged child.
- `text2wave` receives text over stdin, eliminating the leaked temporary text files from the old implementation.
- PipeWire-native `pw-play` is the preferred playback backend, with automatic fallback through other installed players.
- Normal PCM peak normalization is now implemented inside Huuda; SoX is optional rather than mandatory.
- Optional modern Piper support via `--engine piper` with Finnish `fi_FI-harri-medium` as the default model name.
- Finglish replacement retains the hand-tuned, longest-first cascading semantics while avoiding thousands of unnecessary regex calls.
- The invalid empty-string lexicon entry has been removed.
- `--check`, `--debug`, `--dry-run`, `--output`, `--no-play`, explicit player/normalizer selection and stage timeouts have been added.
- `-o/--output` is a real export path: `.wav` is written natively, while `.mp3`, `.flac`, `.ogg`/`.oga`, `.opus`, and `.m4a` are encoded through optional FFmpeg.
- `--bitrate` controls MP3/Opus/M4A output; export is atomic so failed encodes do not replace a good destination file.
- Proper `pyproject.toml` packaging, a `huuda` console command, tests and GitHub Actions CI are included.

## Compatibility

The old invocation remains valid:

```bash
python3 huuda.py --finglish --text "It's very nice here."
```

Installed users can use:

```bash
huuda --finglish "It's very nice here."
```

## First thing to run on a machine where old Huuda hung

```bash
python3 huuda.py --check
```

Then test the exact stages visibly:

```bash
python3 huuda.py --debug --finglish "The computer is extremely sophisticated."
```

If playback is the problem, compare:

```bash
python3 huuda.py --player pw-play "Testi."
python3 huuda.py --player aplay "Testi."
python3 huuda.py --player play "Testi."
```

Every backend has a bounded wait, so a broken player should fail with a named stage instead of holding the terminal indefinitely.
