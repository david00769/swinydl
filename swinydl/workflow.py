from __future__ import annotations

"""Top-level orchestration for inspect, download, process, and transcribe flows."""

from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import uuid

from .app_paths import cache_dir, default_output_root, ensure_runtime_dirs
from .auth import AuthenticatedSession, BrowserSession, CookieSession
from .captions import (
    load_native_caption_segments,
    parse_srt,
    parse_webvtt,
    segments_to_srt,
    segments_to_text,
)
from .discovery import filter_lessons, inspect_course as discover_course, resolve_lesson_assets
from .echo_exceptions import DiscoveryError, NativeCaptionError
from .manifest import build_job_status, load_process_manifest, status_path_for_manifest, write_job_status
from .media import download_lesson_media, select_caption_asset
from .models import (
    CourseManifest,
    DownloadOptions,
    DownloadSummary,
    InspectOptions,
    LessonManifest,
    ProcessManifest,
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
    with BrowserSession(course_url=url) as browser:
        course = filter_lessons(discover_course(url, browser), options)
        return _process_course_with_session(
            session=browser,
            source_page_url=url,
            course=course,
            options=options,
            command="process",
            status_path=None,
        )


def process_manifest(path: Path | str) -> RunSummary:
    """Run a manifest-launched Safari or native-wrapper job without Selenium."""
    manifest = load_process_manifest(path)
    previous_temp_root = os.environ.get("SWINYDL_TEMP_ROOT")
    previous_log_root = os.environ.get("SWINYDL_LOG_ROOT")
    try:
        if manifest.temp_root:
            os.environ["SWINYDL_TEMP_ROOT"] = str(manifest.temp_root)
        if manifest.log_root:
            os.environ["SWINYDL_LOG_ROOT"] = str(manifest.log_root)
        ensure_runtime_dirs()
        if manifest.output_root is None:
            raise ValueError("Process manifest is missing output_root. Choose an output folder in SWinyDL before launching this job.")
        options = ProcessOptions(
            output_root=Path(manifest.output_root or default_output_root()),
            temp_root=manifest.temp_root,
            log_root=manifest.log_root,
            lesson_ids=manifest.selected_lesson_ids,
            transcript_source=manifest.transcript_source,
            asr_backend=manifest.asr_backend,
            diarization_mode=manifest.diarization_mode,
            requested_action=manifest.requested_action,
            delete_downloaded_media=manifest.delete_downloaded_media,
            keep_audio=manifest.keep_audio,
            keep_video=manifest.keep_video,
        )
        session = CookieSession(manifest.cookies)
        course = _course_from_manifest(session, manifest, options)
        return _process_course_with_session(
            session=session,
            source_page_url=manifest.source_page_url,
            course=course,
            options=options,
            command="process-manifest",
            status_path=status_path_for_manifest(manifest.manifest_path or path),
        )
    finally:
        _restore_env("SWINYDL_TEMP_ROOT", previous_temp_root)
        _restore_env("SWINYDL_LOG_ROOT", previous_log_root)


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
            lesson = _resolve_assets_if_possible(browser, lesson)
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


def _process_course_with_session(
    *,
    session: AuthenticatedSession,
    source_page_url: str,
    course: CourseManifest,
    options: ProcessOptions,
    command: str,
    status_path: Path | None,
) -> RunSummary:
    """Process a normalized course through the transcript workflow."""
    output_root = ensure_dir(options.output_root)
    run_id = uuid.uuid4().hex[:12]
    created_at = now_utc().isoformat() + "Z"
    started_at = created_at
    results: list[TranscriptResult] = []
    lesson_states = {
        lesson.lesson_id: {
            "lesson_id": lesson.lesson_id,
            "title": lesson.title,
            "status": "queued",
            "stage": "queued",
            "detail": "Queued and waiting to start.",
            "error": None,
            "transcript_files": [],
            "transcript_folder": None,
            "retained_media_files": [],
        }
        for lesson in course.lessons
    }
    events: list[tuple[str, str, str]] = [
        (created_at, "info", f"Queued {len(course.lessons)} lessons from {course.course_title}.")
    ]
    _write_status_snapshot(
        status_path,
        run_id=run_id,
        command=command,
        course=course,
        source_page_url=source_page_url,
        output_root=output_root,
        started_at=started_at,
        options=options,
        lesson_states=lesson_states,
        events=events,
    )

    for lesson in course.lessons:
        def status_callback(*, lesson_id, title, status, stage, detail, error=None):
            _record_status_update(
                lesson_states=lesson_states,
                events=events,
                lesson_id=lesson_id,
                title=title,
                status=status,
                stage=stage,
                detail=detail,
                error=error,
            )
            _write_status_snapshot(
                status_path,
                run_id=run_id,
                command=command,
                course=course,
                source_page_url=source_page_url,
                output_root=output_root,
                started_at=started_at,
                options=options,
                lesson_states=lesson_states,
                events=events,
                active_lesson_id=lesson_id,
                active_lesson_title=title,
            )

        result = _process_lesson(
            session,
            course,
            lesson,
            options,
            status_callback=status_callback,
        )
        results.append(result)
        _record_result_state(lesson_states, events, result)
        _write_status_snapshot(
            status_path,
            run_id=run_id,
            command=command,
            course=course,
            source_page_url=source_page_url,
            output_root=output_root,
            started_at=started_at,
            options=options,
            lesson_states=lesson_states,
            events=events,
            active_lesson_id=None,
            active_lesson_title=None,
        )

    summary = RunSummary(
        run_id=run_id,
        created_at=created_at,
        command=command,
        course=course,
        results=results,
    )
    _write_run_manifest(output_root, course, run_id, summary)
    _write_status_snapshot(
        status_path,
        run_id=run_id,
        command=command,
        course=course,
        source_page_url=source_page_url,
        output_root=output_root,
        started_at=started_at,
        options=options,
        lesson_states=lesson_states,
        events=events,
        summary_path=(output_root / slugify(course.course_title) / "_runs" / f"{run_id}.json"),
    )
    return summary


def _course_from_manifest(
    session: AuthenticatedSession,
    manifest: ProcessManifest,
    options: ProcessOptions,
) -> CourseManifest:
    """Choose the manifest-provided course or discover one from the authenticated session."""
    if manifest.course is not None:
        return filter_lessons(manifest.course, options)
    discovered = filter_lessons(discover_course(manifest.course_url, session), options)
    if all(lesson.assets for lesson in discovered.lessons):
        return discovered
    raise DiscoveryError("Manifest-driven processing needs pre-resolved lesson assets when no browser is available.")


def _process_lesson(
    session: AuthenticatedSession,
    course: CourseManifest,
    lesson,
    options: ProcessOptions,
    status_callback=None,
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

    lesson = _resolve_assets_if_possible(session, lesson)
    transcript_source = _resolve_transcript_source(options, lesson)

    try:
        if transcript_source == "native":
            if status_callback is not None:
                status_callback(
                    lesson_id=lesson.lesson_id,
                    title=lesson.title,
                    status="running",
                    stage="downloading",
                    detail="Loading native captions from Echo360.",
                )
            caption_asset = select_caption_asset(lesson)
            if caption_asset is None:
                raise NativeCaptionError("Native captions were requested but none were found.")
            segments = load_native_caption_segments(session.requests_session(), caption_asset.url)
            words = []
            language = "en"
            model_name = None
            asr_backend = None
            audio_path = None
            video_paths: list[Path] = []
            downloaded_media_paths: list[Path] = []
            diarized = False
        else:
            temp_dir = ensure_dir(_job_cache_dir(options) / "runs" / f"{key}-{uuid.uuid4().hex[:8]}")
            if status_callback is not None:
                status_callback(
                    lesson_id=lesson.lesson_id,
                    title=lesson.title,
                    status="running",
                    stage="downloading",
                    detail="Downloading lesson audio for transcription.",
                )
            downloaded = download_lesson_media(
                session,
                lesson,
                temp_dir,
                media="audio",
                file_stem=key,
            )
            if not downloaded:
                raise RuntimeError("yt-dlp produced no downloaded media file.")
            normalized_audio = temp_dir / f"{key}.wav"
            if status_callback is not None:
                status_callback(
                    lesson_id=lesson.lesson_id,
                    title=lesson.title,
                    status="running",
                    stage="extracting_audio",
                    detail="Normalizing audio to mono 16 kHz WAV.",
                )
            normalize_media_to_wav(downloaded[0], normalized_audio)
            segments, words, language, diarized, asr_backend, model_name = transcribe_audio(
                normalized_audio,
                asr_backend=options.asr_backend,
                diarization_mode=options.diarization_mode,
                progress_callback=(
                    None
                    if status_callback is None
                    else lambda stage, detail: status_callback(
                        lesson_id=lesson.lesson_id,
                        title=lesson.title,
                        status="running",
                        stage=stage,
                        detail=detail,
                    )
                ),
            )
            audio_path = output_root / f"{key}.wav" if options.keep_audio else None
            if audio_path is not None:
                shutil.copy2(normalized_audio, audio_path)
            video_paths = []
            downloaded_media_paths: list[Path] = []
            if options.requested_action == "download_and_transcribe":
                if not options.delete_downloaded_media:
                    stored_paths = download_lesson_media(
                        session,
                        lesson,
                        output_root,
                        media="both",
                        file_stem=key,
                    )
                    downloaded_media_paths = stored_paths
                    if options.keep_video:
                        video_paths = [path for path in stored_paths if path.suffix.lower() == ".mp4"]
            shutil.rmtree(temp_dir, ignore_errors=True)

        if status_callback is not None:
            status_callback(
                lesson_id=lesson.lesson_id,
                title=lesson.title,
                status="running",
                stage="writing_files",
                detail="Writing transcript artifacts to disk.",
            )
        artifacts = TranscriptArtifacts(
            txt_path=txt_path,
            srt_path=srt_path,
            json_path=json_path,
            audio_path=audio_path,
            video_paths=video_paths,
            downloaded_media_paths=downloaded_media_paths if transcript_source == "asr" else [],
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
    lesson,
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
            temp_dir = ensure_dir(_job_cache_dir(options) / "runs" / f"{key}-{uuid.uuid4().hex[:8]}")
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


def _resolve_transcript_source(options: ProcessOptions, lesson) -> str:
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


def _resolve_assets_if_possible(session: AuthenticatedSession, lesson):
    """Resolve page-level assets only when the session exposes a browser driver."""
    if getattr(session, "driver", None) is None:
        return lesson
    return resolve_lesson_assets(session, lesson)


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


def _job_cache_dir(options: ProcessOptions | TranscribeOptions) -> Path:
    return getattr(options, "temp_root", None) or cache_dir()


def _restore_env(name: str, previous_value: str | None) -> None:
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _write_status_snapshot(
    status_path: Path | None,
    *,
    run_id: str,
    command: str,
    course: CourseManifest,
    source_page_url: str,
    output_root: Path,
    started_at: str,
    options: ProcessOptions,
    lesson_states: dict[str, dict[str, object]],
    events: list[tuple[str, str, str]],
    active_lesson_id: str | None = None,
    active_lesson_title: str | None = None,
    summary_path: Path | None = None,
) -> None:
    """Write a manifest-sidecar job status file when requested."""
    if status_path is None:
        return
    updated_at = now_utc().isoformat() + "Z"
    completed = sum(
        1
        for state in lesson_states.values()
        if str(state["status"]) in {"success", "failed", "skipped"}
    )
    lesson_snapshots = [
        (
            str(lesson_states[lesson.lesson_id]["lesson_id"]),
            str(lesson_states[lesson.lesson_id]["title"]),
            str(lesson_states[lesson.lesson_id]["status"]),
            str(lesson_states[lesson.lesson_id]["stage"]),
            str(lesson_states[lesson.lesson_id]["detail"]) if lesson_states[lesson.lesson_id]["detail"] is not None else None,
            str(lesson_states[lesson.lesson_id]["error"]) if lesson_states[lesson.lesson_id]["error"] is not None else None,
        )
        for lesson in course.lessons
    ]
    lesson_artifacts = [
        (
            [str(path) for path in lesson_states[lesson.lesson_id]["transcript_files"]],
            str(lesson_states[lesson.lesson_id]["transcript_folder"])
            if lesson_states[lesson.lesson_id]["transcript_folder"] is not None
            else None,
            [str(path) for path in lesson_states[lesson.lesson_id]["retained_media_files"]],
        )
        for lesson in course.lessons
    ]
    overall_status = "running"
    error = None
    if completed == len(course.lessons):
        if any(str(state["status"]) == "failed" for state in lesson_states.values()):
            overall_status = "failed"
            error = "One or more lessons failed."
        else:
            overall_status = "success"
    if active_lesson_id is None:
        for lesson in course.lessons:
            state = lesson_states[lesson.lesson_id]
            if str(state["status"]) == "running":
                active_lesson_id = lesson.lesson_id
                active_lesson_title = lesson.title
                break
    started = datetime.fromisoformat(started_at.removesuffix("Z"))
    elapsed_seconds = max(0.0, (now_utc() - started).total_seconds())
    status = build_job_status(
        job_id=run_id,
        command=command,
        overall_status=overall_status,
        course_title=course.course_title,
        source_page_url=source_page_url,
        output_root=output_root,
        total_lessons=len(course.lessons),
        completed_lessons=completed,
        started_at=started_at,
        updated_at=updated_at,
        elapsed_seconds=elapsed_seconds,
        lesson_snapshots=lesson_snapshots,
        lesson_artifacts=lesson_artifacts,
        active_lesson_id=active_lesson_id,
        active_lesson_title=active_lesson_title,
        detail=(
            f"Processing {active_lesson_title}."
            if active_lesson_title and overall_status == "running"
            else ("All selected lessons completed." if overall_status == "success" else None)
        ),
        requested_action=options.requested_action,
        diarization_mode=options.diarization_mode,
        delete_downloaded_media=options.delete_downloaded_media,
        events=events[-12:],
        summary_path=summary_path,
        error=error,
    )
    write_job_status(status_path, status)


def _record_status_update(
    *,
    lesson_states: dict[str, dict[str, object]],
    events: list[tuple[str, str, str]],
    lesson_id: str,
    title: str,
    status: str,
    stage: str,
    detail: str,
    error: str | None = None,
) -> None:
    """Update one lesson snapshot and append a lightweight activity event."""
    state = lesson_states[lesson_id]
    state["title"] = title
    previous_stage = str(state["stage"])
    previous_detail = str(state["detail"]) if state["detail"] is not None else None
    state["status"] = status
    state["stage"] = stage
    state["detail"] = detail
    if error is not None:
        state["error"] = error
    timestamp = now_utc().isoformat() + "Z"
    if stage != previous_stage or detail != previous_detail:
        events.append((timestamp, "info", f"{title}: {detail}"))


def _record_result_state(
    lesson_states: dict[str, dict[str, object]],
    events: list[tuple[str, str, str]],
    result: TranscriptResult,
) -> None:
    """Persist the final lesson outcome into the status snapshot state."""
    state = lesson_states[result.lesson.lesson_id]
    timestamp = now_utc().isoformat() + "Z"
    if result.status == "success":
        state["status"] = "success"
        state["stage"] = "done"
        state["detail"] = "TXT transcript ready. Timed captions and structured JSON are also available."
        state["error"] = None
        state["transcript_files"] = [
            str(result.artifacts.txt_path),
            str(result.artifacts.srt_path),
            str(result.artifacts.json_path),
        ]
        state["transcript_folder"] = str(result.artifacts.txt_path.parent)
        state["retained_media_files"] = [str(path) for path in result.artifacts.downloaded_media_paths]
        events.append((timestamp, "success", f"{result.lesson.title}: transcription complete."))
        return
    if result.status == "skipped":
        state["status"] = "skipped"
        state["stage"] = "done"
        state["detail"] = "Existing TXT transcript reused."
        state["error"] = None
        state["transcript_files"] = [
            str(result.artifacts.txt_path),
            str(result.artifacts.srt_path),
            str(result.artifacts.json_path),
        ]
        state["transcript_folder"] = str(result.artifacts.txt_path.parent)
        events.append((timestamp, "info", f"{result.lesson.title}: reused existing transcript artifacts."))
        return
    state["status"] = "failed"
    state["stage"] = "failed"
    state["detail"] = _categorize_failure_detail(result.error)
    state["error"] = result.error
    events.append((timestamp, "error", f"{result.lesson.title}: {result.error or 'failed'}"))


def _categorize_failure_detail(error: str | None) -> str:
    """Turn raw backend errors into shorter run-state hints."""
    message = (error or "").lower()
    if "assets were not found" in message or "bootstrap-models" in message:
        return "Required model artifacts are missing. Run bootstrap-models and retry."
    if "ffmpeg" in message:
        return "Audio conversion failed. Check the ffmpeg installation and retry."
    if "unable to launch" in message or "python backend" in message:
        return "The native app could not launch the Python backend."
    if "cookie" in message or "login" in message or "caption" in message:
        return "The authenticated lesson assets could not be loaded."
    return "Transcription failed. Open the error details and retry."
