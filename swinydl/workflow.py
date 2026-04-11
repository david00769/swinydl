from __future__ import annotations

"""Top-level orchestration for inspect, download, process, and transcribe flows."""

from pathlib import Path
import json
import shutil
import uuid

from .app_paths import cache_dir, ensure_runtime_dirs
from .auth import BrowserSession
from .captions import (
    load_native_caption_segments,
    parse_srt,
    parse_webvtt,
    segments_to_srt,
    segments_to_text,
)
from .discovery import filter_lessons, inspect_course as discover_course, resolve_lesson_assets
from .echo_exceptions import NativeCaptionError
from .media import download_lesson_media, select_caption_asset
from .models import (
    CourseManifest,
    DownloadOptions,
    DownloadSummary,
    InspectOptions,
    LessonManifest,
    ProcessOptions,
    RunSummary,
    TranscriptArtifacts,
    TranscriptResult,
    TranscribeOptions,
)
from .transcription import (
    diarization_runtime_status,
    normalize_media_to_wav,
    transcribe_audio,
)
from .utils import ensure_dir, export_dataclass, json_dumps, lesson_key, now_utc, slugify


def inspect_course(url: str, options: InspectOptions | None = None) -> CourseManifest:
    """Inspect an Echo360 course and return the filtered lesson manifest."""
    options = options or InspectOptions()
    ensure_runtime_dirs()
    with BrowserSession(course_url=url) as browser:
        course = discover_course(url, browser)
    return filter_lessons(course, options)


def process_course(url: str, options: ProcessOptions) -> RunSummary:
    """Run the transcript-first workflow for every selected lesson in a course."""
    ensure_runtime_dirs()
    output_root = ensure_dir(options.output_root)
    run_id = uuid.uuid4().hex[:12]
    created_at = now_utc().isoformat() + "Z"

    with BrowserSession(course_url=url) as browser:
        course = filter_lessons(discover_course(url, browser), options)
        results = [
            _process_lesson(browser, course, lesson, options)
            for lesson in course.lessons
        ]

    summary = RunSummary(
        run_id=run_id,
        created_at=created_at,
        command="process",
        course=course,
        results=results,
    )
    _write_run_manifest(output_root, course, run_id, summary)
    return summary


def download_course(url: str, options: DownloadOptions) -> DownloadSummary:
    """Download explicit Echo360 media artifacts for the selected lessons."""
    ensure_runtime_dirs()
    output_root = ensure_dir(options.output_root)
    run_id = uuid.uuid4().hex[:12]
    created_at = now_utc().isoformat() + "Z"
    downloads: list[dict[str, object]] = []

    with BrowserSession(course_url=url) as browser:
        course = filter_lessons(discover_course(url, browser), options)
        course_dir = ensure_dir(output_root / slugify(course.course_title))
        for lesson in course.lessons:
            lesson = resolve_lesson_assets(browser, lesson)
            key = lesson_key(lesson.date, lesson.lesson_id, lesson.index, lesson.title)
            artifacts = download_lesson_media(
                browser,
                lesson,
                course_dir,
                media=options.media,
                file_stem=key,
            )
            downloads.append(
                {
                    "lesson_id": lesson.lesson_id,
                    "title": lesson.title,
                    "media": options.media,
                    "artifacts": [str(path) for path in artifacts],
                }
            )

    summary = DownloadSummary(
        run_id=run_id,
        created_at=created_at,
        command="download",
        course=course,
        downloads=downloads,
    )
    _write_run_manifest(output_root, course, run_id, summary)
    return summary


def transcribe_file(path: Path | str, options: TranscribeOptions) -> TranscriptResult:
    """Run the transcript workflow for one local media or caption file."""
    ensure_runtime_dirs()
    source = Path(path).expanduser().resolve()
    lesson = LessonManifest(
        lesson_id=source.stem,
        title=source.stem,
        date=None,
        lesson_url=str(source),
        index=1,
    )
    course = CourseManifest(
        source_url=str(source),
        hostname="local-file",
        platform="local",
        course_uuid="local",
        course_id=None,
        course_title="Local Files",
        lessons=[lesson],
    )
    return _process_local_media(course, lesson, source, options)


def _process_lesson(
    browser: BrowserSession,
    course: CourseManifest,
    lesson: LessonManifest,
    options: ProcessOptions,
) -> TranscriptResult:
    """Process one Echo360 lesson into transcript artifacts and structured JSON."""
    output_root = ensure_dir(options.output_root / slugify(course.course_title))
    key = lesson_key(lesson.date, lesson.lesson_id, lesson.index, lesson.title)
    txt_path = output_root / f"{key}.txt"
    srt_path = output_root / f"{key}.srt"
    json_path = output_root / f"{key}.json"

    if json_path.exists() and not options.force:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if payload.get("status") == "success":
                return TranscriptResult(
                    status="skipped",
                    lesson=lesson,
                    transcript_source=payload.get("transcript_source", "auto"),
                    asr_backend=payload.get("asr_backend"),
                    language=payload.get("language"),
                    diarized=bool(payload.get("diarized", False)),
                    model_name=payload.get("model_name"),
                    duration=payload.get("duration"),
                    segments=[],
                    words=[],
                    artifacts=TranscriptArtifacts(txt_path=txt_path, srt_path=srt_path, json_path=json_path),
                )
        except Exception:
            pass

    lesson = resolve_lesson_assets(browser, lesson)
    session = browser.requests_session()
    transcript_source = _resolve_transcript_source(options, lesson)

    try:
        if transcript_source == "native":
            caption_asset = select_caption_asset(lesson)
            if caption_asset is None:
                raise NativeCaptionError("Native captions were requested but none were found.")
            segments = load_native_caption_segments(session, caption_asset.url)
            words = []
            language = "en"
            model_name = None
            asr_backend = None
            audio_path = None
            diarized = False
        else:
            temp_dir = ensure_dir(cache_dir() / "runs" / key)
            downloaded = download_lesson_media(
                browser,
                lesson,
                temp_dir,
                media="audio",
                file_stem=key,
            )
            if not downloaded:
                raise RuntimeError("yt-dlp produced no downloaded media file.")
            normalized_audio = temp_dir / f"{key}.wav"
            normalize_media_to_wav(downloaded[0], normalized_audio)
            segments, words, language, diarized, asr_backend, model_name = transcribe_audio(
                normalized_audio,
                asr_backend=options.asr_backend,
                diarization_mode=options.diarization_mode,
            )
            audio_path = output_root / f"{key}.wav" if options.keep_audio else None
            if audio_path is not None:
                shutil.copy2(normalized_audio, audio_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

        artifacts = TranscriptArtifacts(
            txt_path=txt_path,
            srt_path=srt_path,
            json_path=json_path,
            audio_path=audio_path,
        )
        result = TranscriptResult(
            status="success",
            lesson=lesson,
            transcript_source=transcript_source,
            asr_backend=asr_backend,
            language=language,
            diarized=diarized,
            model_name=model_name,
            duration=segments[-1].end if segments else None,
            segments=segments,
            words=words,
            artifacts=artifacts,
        )
        _write_transcript_artifacts(result)
        return result
    except Exception as exc:
        artifacts = TranscriptArtifacts(txt_path=txt_path, srt_path=srt_path, json_path=json_path)
        failed = TranscriptResult(
            status="failed",
            lesson=lesson,
            transcript_source=transcript_source,
            asr_backend=options.asr_backend if transcript_source == "asr" else None,
            language=None,
            diarized=options.diarization_mode == "on",
            model_name=None,
            duration=None,
            segments=[],
            words=[],
            artifacts=artifacts,
            error=str(exc),
        )
        _write_transcript_artifacts(failed)
        return failed


def _process_local_media(
    course: CourseManifest,
    lesson: LessonManifest,
    source: Path,
    options: TranscribeOptions,
) -> TranscriptResult:
    """Process one local file into transcript artifacts and structured JSON."""
    output_root = ensure_dir(options.output_root / slugify(course.course_title))
    key = lesson_key(None, lesson.lesson_id, lesson.index, lesson.title)
    txt_path = output_root / f"{key}.txt"
    srt_path = output_root / f"{key}.srt"
    json_path = output_root / f"{key}.json"
    transcript_source = "native" if source.suffix.lower() in {".vtt", ".srt"} else "asr"

    try:
        if transcript_source == "native":
            caption_text = source.read_text(encoding="utf-8")
            segments = parse_srt(caption_text) if source.suffix.lower() == ".srt" else parse_webvtt(caption_text)
            words: list = []
            language = "en"
            model_name = None
            asr_backend = None
            audio_path = None
            diarized = False
        else:
            temp_dir = ensure_dir(cache_dir() / "runs" / key)
            normalized_audio = temp_dir / f"{key}.wav"
            normalize_media_to_wav(source, normalized_audio)
            segments, words, language, diarized, asr_backend, model_name = transcribe_audio(
                normalized_audio,
                asr_backend=options.asr_backend,
                diarization_mode=options.diarization_mode,
            )
            audio_path = output_root / f"{key}.wav" if options.keep_audio else None
            if audio_path is not None:
                shutil.copy2(normalized_audio, audio_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

        result = TranscriptResult(
            status="success",
            lesson=lesson,
            transcript_source=transcript_source,
            asr_backend=asr_backend,
            language=language,
            diarized=diarized,
            model_name=model_name,
            duration=segments[-1].end if segments else None,
            segments=segments,
            words=words,
            artifacts=TranscriptArtifacts(
                txt_path=txt_path,
                srt_path=srt_path,
                json_path=json_path,
                audio_path=audio_path,
            ),
        )
        _write_transcript_artifacts(result)
        return result
    except Exception as exc:
        failed = TranscriptResult(
            status="failed",
            lesson=lesson,
            transcript_source=transcript_source,
            asr_backend=options.asr_backend if transcript_source == "asr" else None,
            language=None,
            diarized=options.diarization_mode == "on",
            model_name=None,
            duration=None,
            segments=[],
            words=[],
            artifacts=TranscriptArtifacts(
                txt_path=txt_path,
                srt_path=srt_path,
                json_path=json_path,
            ),
            error=str(exc),
        )
        _write_transcript_artifacts(failed)
        return failed


def _resolve_transcript_source(options: ProcessOptions, lesson: LessonManifest) -> str:
    """Choose between native captions and ASR for one lesson."""
    diarization_ready, _ = diarization_runtime_status(require_token=False)
    if options.diarization_mode == "on":
        return "asr"
    if options.diarization_mode == "auto" and diarization_ready:
        return "asr"
    if options.transcript_source == "asr":
        return "asr"
    if options.transcript_source == "native":
        return "native"
    return "native" if select_caption_asset(lesson) is not None else "asr"


def _write_transcript_artifacts(result: TranscriptResult) -> None:
    """Write `.txt`, `.srt`, and `.json` transcript outputs for a result."""
    ensure_dir(result.artifacts.txt_path.parent)
    if result.status == "success":
        result.artifacts.txt_path.write_text(
            segments_to_text(result.segments), encoding="utf-8"
        )
        result.artifacts.srt_path.write_text(
            segments_to_srt(result.segments), encoding="utf-8"
        )
    payload = export_dataclass(result)
    result.artifacts.json_path.write_text(json_dumps(payload), encoding="utf-8")


def _write_run_manifest(
    output_root: Path,
    course: CourseManifest,
    run_id: str,
    summary: RunSummary | DownloadSummary,
) -> None:
    """Write the per-run manifest under the course `_runs` directory."""
    course_dir = ensure_dir(output_root / slugify(course.course_title) / "_runs")
    (course_dir / f"{run_id}.json").write_text(
        json_dumps(export_dataclass(summary)),
        encoding="utf-8",
    )
