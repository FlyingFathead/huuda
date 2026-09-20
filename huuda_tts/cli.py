from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import sysconfig
from pathlib import Path

from . import __version__
from .audio import export_audio, normalize_audio, play_audio
from .diagnostics import dependency_report, festival_smoke_test
from .errors import HuudaError
from .process import ProcessRunner
from .replacements import ReplacementTable
from .synthesis import (
    DEFAULT_FESTIVAL_VOICE,
    DEFAULT_PIPER_MODEL,
    FestivalEngine,
    PiperEngine,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def default_replacement_file() -> Path:
    # Source checkout / editable install.
    source_path = PROJECT_ROOT / "wordreplacement.json"
    if source_path.is_file():
        return source_path

    # Regular wheel install via setuptools data-files.
    installed = Path(sysconfig.get_path("data")) / "share" / "huuda" / "wordreplacement.json"
    return installed


DEFAULT_REPLACEMENT_FILE = default_replacement_file()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="huuda",
        description="Huuda v0.1.0 - Finnish/Finglish command-line speech synthesis",
    )
    parser.add_argument("message", nargs="*", help="text to speak (positional form)")
    parser.add_argument("--text", "-t", "--t", help="text to speak")
    parser.add_argument("--inputfile", "--file", "-f", dest="inputfile", help="read text from file, or - for stdin")

    parser.add_argument(
        "--english", "--eng", "--en", "--e", "--finglish",
        dest="replace_english", action="store_true",
        help="apply the Finglish pronunciation replacement table",
    )
    parser.add_argument(
        "--replacement-file", "--replacement_file",
        type=Path, default=DEFAULT_REPLACEMENT_FILE,
        help=f"replacement JSON (default: {DEFAULT_REPLACEMENT_FILE})",
    )

    parser.add_argument("--engine", choices=("festival", "piper"), default="festival")
    parser.add_argument("--voice", default=DEFAULT_FESTIVAL_VOICE, help="Festival voice expression")
    parser.add_argument("--piper-model", default=DEFAULT_PIPER_MODEL, help="Piper model name/path")
    parser.add_argument("--cuda", action="store_true", help="use CUDA with Piper")

    parser.add_argument(
        "--output", "-o", type=Path,
        help="write audio file (.wav, .mp3, .flac, .ogg/.oga, .opus, or .m4a)",
    )
    parser.add_argument(
        "--bitrate", default="192k",
        help="bitrate for MP3/Opus/M4A output (default: 192k; OGG uses Vorbis quality mode)",
    )
    parser.add_argument("--no-play", action="store_true", help="synthesize without playing audio")
    parser.add_argument(
        "--player", default="auto",
        choices=("auto", "pw-play", "paplay", "aplay", "play", "ffplay", "afplay", "none"),
        help="audio playback backend (auto prefers PipeWire pw-play)",
    )
    parser.add_argument("--no-normalize", action="store_true", help="skip peak normalization")
    parser.add_argument("--normalizer", choices=("auto", "python", "sox"), default="auto", help="normalization backend")
    parser.add_argument("--blast", action="store_true", help="normalize closer to 0 dBFS")

    parser.add_argument("--timeout", type=float, default=30.0, help="synthesis/processing timeout in seconds")
    parser.add_argument("--playback-timeout", type=float, help="override automatic playback timeout")
    parser.add_argument("--dry-run", action="store_true", help="print prepared text and exit")
    parser.add_argument("--debug", action="store_true", help="show timings and replacement hits")
    parser.add_argument("--quiet", action="store_true", help="suppress normal stage messages")
    parser.add_argument("--check", action="store_true", help="diagnose dependencies and run a bounded Festival smoke test")
    parser.add_argument("--version", action="version", version=f"Huuda {__version__}")
    return parser


def read_input(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    provided = int(bool(args.text)) + int(bool(args.inputfile)) + int(bool(args.message))
    if provided > 1:
        parser.error("use only one input source: positional text, --text, or --file")
    if args.text:
        return args.text
    if args.message:
        return " ".join(args.message)
    if args.inputfile:
        if args.inputfile == "-":
            return sys.stdin.read()
        try:
            return Path(args.inputfile).read_text(encoding="utf-8")
        except OSError as exc:
            raise HuudaError(f"unable to read input file {args.inputfile}: {exc}") from exc
    parser.error("text is required unless --check is used")
    raise AssertionError("unreachable")


def prepare_text(text: str, args: argparse.Namespace) -> str:
    if not args.replace_english:
        return text
    table = ReplacementTable.load(args.replacement_file)
    prepared, stats = table.apply(text, debug=args.debug)
    if args.debug:
        print(
            f"[huuda] Finglish: {stats.loaded} rules loaded, "
            f"{stats.matched_rules} matched, {stats.replacements} replacements"
        )
    return prepared


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.playback_timeout is not None and args.playback_timeout <= 0:
        parser.error("--playback-timeout must be greater than zero")

    if args.check:
        for line in dependency_report(args.replacement_file):
            print(line)
        print(festival_smoke_test(timeout=min(args.timeout, 10.0), voice=args.voice))
        return 0

    text = prepare_text(read_input(args, parser), args)
    if not text.strip():
        raise HuudaError("text to speak is empty")

    if args.debug or args.dry_run:
        print(f"[huuda] prepared text: {text!r}")
    if args.dry_run:
        return 0

    runner = ProcessRunner()
    with tempfile.TemporaryDirectory(prefix="huuda-") as tmpdir:
        tmp = Path(tmpdir)
        raw_wav = tmp / "synth.wav"

        if not args.quiet:
            print(f"[huuda] synthesizing with {args.engine}...", file=sys.stderr)

        if args.engine == "festival":
            syn = FestivalEngine(runner).synthesize(
                text, raw_wav, voice=args.voice, timeout=args.timeout
            )
        else:
            syn = PiperEngine(runner).synthesize(
                text,
                raw_wav,
                model=args.piper_model,
                timeout=args.timeout,
                cuda=args.cuda,
            )

        if args.debug:
            print(f"[huuda] synthesis: {syn.elapsed:.2f}s, {raw_wav.stat().st_size} bytes", file=sys.stderr)

        # Always keep the post-processed playback master as WAV. Exporting to
        # MP3/etc. is a separate final stage, so playback never depends on a
        # compressed-format decoder.
        final_wav = tmp / "final.wav"

        if args.no_normalize:
            shutil.copyfile(raw_wav, final_wav)
            norm_elapsed = 0.0
            norm_backend = "none"
        else:
            norm_backend, norm_elapsed = normalize_audio(
                raw_wav,
                final_wav,
                runner=runner,
                timeout=args.timeout,
                blast=args.blast,
                backend=args.normalizer,
            )

        if args.debug:
            print(
                f"[huuda] audio processing: {norm_backend}, {norm_elapsed:.2f}s",
                file=sys.stderr,
            )

        if args.output:
            output_path = args.output.expanduser().resolve()
            out_format, out_elapsed = export_audio(
                final_wav,
                output_path,
                runner=runner,
                timeout=args.timeout,
                bitrate=args.bitrate,
            )
            if not args.quiet:
                print(f"[huuda] wrote {out_format.upper()} {output_path}", file=sys.stderr)
            if args.debug:
                print(f"[huuda] export: {out_format}, {out_elapsed:.2f}s", file=sys.stderr)

        if not args.no_play and args.player != "none":
            if not args.quiet:
                print(f"[huuda] playing ({args.player})...", file=sys.stderr)
            player_name, elapsed = play_audio(
                final_wav,
                runner=runner,
                player=args.player,
                timeout=args.playback_timeout,
            )
            if args.debug:
                print(f"[huuda] playback: {player_name}, {elapsed:.2f}s", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args, parser)
    except KeyboardInterrupt:
        print("\n[huuda] interrupted; child process terminated", file=sys.stderr)
        return 130
    except HuudaError as exc:
        print(f"[huuda] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
