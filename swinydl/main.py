from __future__ import annotations

"""CLI entrypoint for the SWinyDL transcript workflow."""

import argparse
import sys
from pathlib import Path

from .app_paths import default_output_root
from .echo_exceptions import Echo360Error
from .models import DownloadOptions, InspectOptions, ProcessOptions, TranscribeOptions
from .system import configure_runtime_ssl
from .utils import export_dataclass, json_dumps, parse_date
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level CLI parser and subcommands."""
    parser = argparse.ArgumentParser(
        prog="swinydl",
        description=(
            "SWinyDL: transcript-first Echo360 CLI for macOS Apple Silicon.\n\n"
            "Preferred interactive usage is the Safari wrapper and Safari Web Extension.\n"
            "Run ./install.sh from the copied SWinyDL folder or source checkout to set up the local Python runtime, speech models, and Safari app.\n"
            "CLI usage is still supported for fallback and automation. When running from the SWinyDL folder, prefix commands with uv run.\n\n"
            "Common direct CLI usage:\n"
            "  uv run swinydl process COURSE_URL\n"
            "Safari/native-app job execution:\n"
            "  uv run swinydl process-manifest /path/to/job.json\n"
            "or the legacy guided Chrome launcher:\n"
            "  uv run app.py\n\n"
            "The Safari path launches jobs from a logged-in Safari page through the native wrapper app. "
            "The guided launcher remains available as a Chrome-based fallback that captures the current browser URL "
            "and runs the default process workflow against it. Generated outputs include TXT, SRT, and JSON, with TXT as the primary transcript."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Setup:\n"
            "  ./install.sh\n\n"
            "Common flows:\n"
            "  uv run swinydl inspect COURSE_URL\n"
            "  uv run swinydl process COURSE_URL\n"
            "  uv run swinydl process-manifest /path/to/job.json\n"
            "  uv run swinydl download COURSE_URL --media audio\n"
            "  uv run swinydl transcribe /path/to/local/file.mp4\n"
            "  uv run swinydl bootstrap-models\n"
            "  uv run swinydl doctor"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect course lessons and assets.")
    _add_course_and_filters(inspect_parser)
    inspect_parser.add_argument("--json", action="store_true", dest="json_output")

    process_parser = subparsers.add_parser("process", help="Generate transcripts from a course.")
    _add_course_and_filters(process_parser)
    _add_output(process_parser)
    _add_asr_options(process_parser)
    process_parser.add_argument(
        "--transcript-source",
        choices=("auto", "native", "asr"),
        default="auto",
    )
    process_parser.add_argument("--force-asr", action="store_true")
    process_parser.add_argument("--keep-audio", action="store_true")
    process_parser.add_argument("--force", action="store_true")

    manifest_parser = subparsers.add_parser(
        "process-manifest",
        help="Process a Safari/native-wrapper manifest without launching a browser.",
    )
    manifest_parser.add_argument("manifest_path")

    download_parser = subparsers.add_parser("download", help="Explicitly download Echo360 media.")
    _add_course_and_filters(download_parser)
    _add_output(download_parser)
    download_parser.add_argument("--media", choices=("audio", "video", "both"), default="audio")
    download_parser.add_argument("--keep-audio", action="store_true")
    download_parser.add_argument("--keep-video", action="store_true")
    download_parser.add_argument("--force", action="store_true")

    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe a local media file.")
    transcribe_parser.add_argument("path")
    _add_output(transcribe_parser)
    _add_asr_options(transcribe_parser)
    transcribe_parser.add_argument("--keep-audio", action="store_true")
    transcribe_parser.add_argument("--force", action="store_true")

    bootstrap_parser = subparsers.add_parser("bootstrap-models", help="Download staged CoreML model bundles.")
    bootstrap_parser.add_argument(
        "--target",
        choices=("all", "parakeet", "diarizer"),
        default="all",
        help="Select which staged model bundle to download.",
    )
    bootstrap_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch files even if they already exist locally.",
    )

    doctor_parser = subparsers.add_parser("doctor", help="Show runtime dependency status.")
    doctor_parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a shell-style exit code."""
    configure_runtime_ssl()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"inspect", "process", "process-manifest", "download", "transcribe", "bootstrap-models", "doctor", "--version", "-h", "--help"}:
        argv.insert(0, "process")

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command is not None:
            from .bootstrap import ensure_runtime_model_artifacts

            bootstrap_report = ensure_runtime_model_artifacts(args.command)
            if bootstrap_report and bootstrap_report.get("bootstrapped"):
                print(
                    f"Bootstrapping local CoreML models for `{bootstrap_report.get('target', 'all')}`...",
                    file=sys.stderr,
                )

        if args.command == "inspect":
            from .workflow import inspect_course

            options = InspectOptions(
                lesson_ids=tuple(args.lesson_id or ()),
                title_match=args.title_match,
                after_date=parse_date(args.after_date),
                before_date=parse_date(args.before_date),
                latest=args.latest,
                limit=args.limit,
                json_output=args.json_output,
            )
            course = inspect_course(args.course_url, options)
            if args.json_output:
                print(json_dumps(export_dataclass(course)))
            else:
                _print_course(course)
            return 0

        if args.command == "process":
            from .workflow import process_course

            transcript_source = "asr" if args.force_asr else args.transcript_source
            options = ProcessOptions(
                output_root=Path(args.output or default_output_root()),
                lesson_ids=tuple(args.lesson_id or ()),
                title_match=args.title_match,
                after_date=parse_date(args.after_date),
                before_date=parse_date(args.before_date),
                latest=args.latest,
                limit=args.limit,
                transcript_source=transcript_source,
                asr_backend=args.asr_backend,
                diarization_mode=args.diarization,
                keep_audio=args.keep_audio,
                force=args.force,
            )
            summary = process_course(args.course_url, options)
            _print_process_summary(summary)
            return 1 if any(result.status == "failed" for result in summary.results) else 0

        if args.command == "process-manifest":
            from .workflow import process_manifest

            summary = process_manifest(args.manifest_path)
            _print_process_summary(summary)
            return 1 if any(result.status == "failed" for result in summary.results) else 0

        if args.command == "download":
            from .workflow import download_course

            options = DownloadOptions(
                output_root=Path(args.output or default_output_root()),
                lesson_ids=tuple(args.lesson_id or ()),
                title_match=args.title_match,
                after_date=parse_date(args.after_date),
                before_date=parse_date(args.before_date),
                latest=args.latest,
                limit=args.limit,
                media=args.media,
                keep_audio=args.keep_audio,
                keep_video=args.keep_video,
                force=args.force,
            )
            summary = download_course(args.course_url, options)
            print(json_dumps(export_dataclass(summary)))
            return 0

        if args.command == "transcribe":
            from .workflow import transcribe_file

            options = TranscribeOptions(
                output_root=Path(args.output or default_output_root()),
                asr_backend=args.asr_backend,
                diarization_mode=args.diarization,
                keep_audio=args.keep_audio,
                force=args.force,
            )
            result = transcribe_file(args.path, options)
            print(json_dumps(export_dataclass(result)))
            return 1 if result.status == "failed" else 0

        if args.command == "bootstrap-models":
            from .bootstrap import bootstrap_models

            report = bootstrap_models(target=args.target, force=args.force)
            print(json_dumps(report))
            return 0

        if args.command == "doctor":
            from .health import doctor, format_doctor_report
            import json

            report = doctor()
            if args.json_output:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(format_doctor_report(report))
            return 0
    except Echo360Error as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


def _add_course_and_filters(parser: argparse.ArgumentParser) -> None:
    """Attach the shared course URL and lesson-filter arguments."""
    parser.add_argument("course_url")
    parser.add_argument("--lesson-id", action="append")
    parser.add_argument("--title-match")
    parser.add_argument("--after-date")
    parser.add_argument("--before-date")
    parser.add_argument("--latest", type=int)
    parser.add_argument("--limit", type=int)


def _add_output(parser: argparse.ArgumentParser) -> None:
    """Attach the shared output directory flag."""
    parser.add_argument("--output", "-o")


def _add_asr_options(parser: argparse.ArgumentParser) -> None:
    """Attach ASR backend and speaker-separation flags."""
    parser.add_argument(
        "--asr-backend",
        choices=("auto", "parakeet"),
        default="auto",
        help="Select the ASR backend. 'auto' resolves to the local Parakeet CoreML runner.",
    )
    parser.add_argument(
        "--diarization",
        choices=("auto", "on", "off"),
        default="on",
        help="Speaker separation mode. 'on' is the default and uses the local CoreML diarizer.",
    )


def _print_course(course) -> None:
    """Print a compact lesson inventory for `swinydl inspect`."""
    print(f"Course: {course.course_title}")
    print(f"Platform: {course.platform}")
    print(f"Lessons: {len(course.lessons)}")
    for lesson in course.lessons:
        captions = sum(1 for asset in lesson.assets if asset.kind == "caption")
        media = sum(1 for asset in lesson.assets if asset.kind == "media")
        print(f"- {lesson.lesson_id} | {lesson.date or 'undated'} | {lesson.title} | media={media} captions={captions}")


def _print_process_summary(summary) -> None:
    """Print one-line per-lesson status for `swinydl process`."""
    print(f"Course: {summary.course.course_title}")
    for result in summary.results:
        backend = f", backend={result.asr_backend}" if result.asr_backend else ""
        diarized = ", diarized" if result.diarized else ""
        print(f"- {result.lesson.lesson_id}: {result.status} ({result.transcript_source}{backend}{diarized})")
        if result.error:
            print(f"  error: {result.error}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
