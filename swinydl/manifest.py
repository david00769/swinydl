from __future__ import annotations

"""Manifest and job-status helpers shared by the CLI and Safari bridge."""

from pathlib import Path
import json

from .models import (
    BrowserCookie,
    CourseManifest,
    JobStatus,
    JobStatusEvent,
    JobStatusLesson,
    LessonAsset,
    LessonManifest,
    ProcessManifest,
)
from .utils import ensure_dir, export_dataclass, json_dumps


def load_process_manifest(path: Path | str) -> ProcessManifest:
    """Load a process manifest from JSON on disk."""
    manifest_path = Path(path).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    course_payload = payload.get("course")
    return ProcessManifest(
        source_page_url=payload["source_page_url"],
        course_url=payload["course_url"],
        host=payload.get("host") or "",
        selected_lesson_ids=tuple(payload.get("selected_lesson_ids") or ()),
        requested_action=payload.get("requested_action", "transcribe"),
        delete_downloaded_media=bool(payload.get("delete_downloaded_media", True)),
        cookies=[_cookie_from_dict(item) for item in payload.get("cookies", [])],
        course=_course_from_dict(course_payload) if course_payload else None,
        output_root=Path(payload["output_root"]).expanduser() if payload.get("output_root") else None,
        temp_root=Path(payload["temp_root"]).expanduser() if payload.get("temp_root") else None,
        log_root=Path(payload["log_root"]).expanduser() if payload.get("log_root") else None,
        keep_audio=bool(payload.get("keep_audio", False)),
        keep_video=bool(payload.get("keep_video", False)),
        transcript_source=payload.get("transcript_source", "auto"),
        asr_backend=payload.get("asr_backend", "auto"),
        diarization_mode=payload.get("diarization_mode", "on"),
        manifest_path=manifest_path,
    )


def status_path_for_manifest(manifest_path: Path | str) -> Path:
    """Return the sidecar status-file path for one manifest."""
    manifest_path = Path(manifest_path).expanduser().resolve()
    return manifest_path.with_suffix(".status.json")


def write_job_status(status_path: Path | str, status: JobStatus) -> None:
    """Write the current job status in deterministic JSON form."""
    path = Path(status_path).expanduser().resolve()
    ensure_dir(path.parent)
    payload = export_dataclass(status)
    path.write_text(json_dumps(payload) + "\n", encoding="utf-8")


def build_job_status(
    *,
    job_id: str,
    command: str,
    overall_status: str,
    course_title: str,
    source_page_url: str,
    output_root: Path,
    total_lessons: int,
    completed_lessons: int,
    started_at: str,
    updated_at: str,
    elapsed_seconds: float,
    lesson_snapshots: list[tuple[str, str, str, str, str | None, str | None]],
    lesson_artifacts: list[tuple[list[str], str | None, list[str]]] | None = None,
    active_lesson_id: str | None = None,
    active_lesson_title: str | None = None,
    detail: str | None = None,
    requested_action: str = "transcribe",
    diarization_mode: str = "on",
    delete_downloaded_media: bool = True,
    events: list[tuple[str, str, str]] | None = None,
    summary_path: Path | None = None,
    error: str | None = None,
) -> JobStatus:
    """Construct one serializable job-status snapshot."""
    return JobStatus(
        job_id=job_id,
        command=command,
        overall_status=overall_status,
        course_title=course_title,
        source_page_url=source_page_url,
        output_root=output_root,
        total_lessons=total_lessons,
        completed_lessons=completed_lessons,
        started_at=started_at,
        updated_at=updated_at,
        elapsed_seconds=elapsed_seconds,
        active_lesson_id=active_lesson_id,
        active_lesson_title=active_lesson_title,
        detail=detail,
        requested_action=requested_action,
        diarization_mode=diarization_mode,
        delete_downloaded_media=delete_downloaded_media,
        lessons=[
            JobStatusLesson(
                lesson_id=lesson_id,
                title=title,
                status=status,
                stage=stage,
                detail=lesson_detail,
                error=lesson_error,
                transcript_files=lesson_artifacts[index][0] if lesson_artifacts is not None else [],
                transcript_folder=lesson_artifacts[index][1] if lesson_artifacts is not None else None,
                retained_media_files=lesson_artifacts[index][2] if lesson_artifacts is not None else [],
            )
            for index, (lesson_id, title, status, stage, lesson_detail, lesson_error) in enumerate(lesson_snapshots)
        ],
        events=[
            JobStatusEvent(timestamp=timestamp, level=level, message=message)
            for timestamp, level, message in (events or [])
        ],
        summary_path=summary_path,
        error=error,
    )


def _cookie_from_dict(payload: dict[str, object]) -> BrowserCookie:
    """Normalize JSON cookie payloads into the backend cookie model."""
    return BrowserCookie(
        name=str(payload["name"]),
        value=str(payload["value"]),
        domain=str(payload["domain"]),
        path=str(payload.get("path") or "/"),
        secure=bool(payload.get("secure", False)),
        http_only=bool(payload.get("http_only", payload.get("httpOnly", False))),
        expiry=_coerce_int(payload.get("expiry", payload.get("expirationDate"))),
        same_site=str(payload["same_site"]) if payload.get("same_site") else (
            str(payload["sameSite"]) if payload.get("sameSite") else None
        ),
    )


def _course_from_dict(payload: dict[str, object]) -> CourseManifest:
    """Rebuild a normalized course manifest from plain JSON."""
    lessons = [_lesson_from_dict(item) for item in payload.get("lessons", [])]
    return CourseManifest(
        source_url=str(payload["source_url"]),
        hostname=str(payload["hostname"]),
        platform=str(payload["platform"]),
        course_uuid=str(payload["course_uuid"]),
        course_id=str(payload["course_id"]) if payload.get("course_id") is not None else None,
        course_title=str(payload["course_title"]),
        lessons=lessons,
    )


def _lesson_from_dict(payload: dict[str, object]) -> LessonManifest:
    """Rebuild one lesson manifest from JSON."""
    assets = [_asset_from_dict(item) for item in payload.get("assets", [])]
    return LessonManifest(
        lesson_id=str(payload["lesson_id"]),
        title=str(payload["title"]),
        date=str(payload["date"]) if payload.get("date") is not None else None,
        lesson_url=str(payload["lesson_url"]),
        index=int(payload["index"]),
        assets=assets,
        source_payload=dict(payload.get("source_payload") or {}),
    )


def _asset_from_dict(payload: dict[str, object]) -> LessonAsset:
    """Rebuild one lesson asset from JSON."""
    return LessonAsset(
        kind=str(payload["kind"]),
        url=str(payload["url"]),
        label=str(payload["label"]) if payload.get("label") is not None else None,
        ext=str(payload["ext"]) if payload.get("ext") is not None else None,
    )


def _coerce_int(value: object) -> int | None:
    """Coerce JSON numeric-like values into integers when present."""
    if value in {None, ""}:
        return None
    return int(value)
