from __future__ import annotations

"""Dataclasses shared across the CLI, workflow, and public Python API."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class LessonAsset:
    """A discovered caption or media asset associated with a lesson."""

    kind: str
    url: str
    label: str | None = None
    ext: str | None = None


@dataclass
class LessonManifest:
    """Normalized lesson metadata produced by Echo360 discovery."""

    lesson_id: str
    title: str
    date: str | None
    lesson_url: str
    index: int
    assets: list[LessonAsset] = field(default_factory=list)
    source_payload: dict[str, Any] = field(
        default_factory=dict, repr=False, compare=False, metadata={"export": False}
    )


@dataclass
class CourseManifest:
    """Normalized course metadata plus the discovered lesson inventory."""

    source_url: str
    hostname: str
    platform: str
    course_uuid: str
    course_id: str | None
    course_title: str
    lessons: list[LessonManifest]


@dataclass
class SelectionOptions:
    """Lesson-selection filters shared by inspect, process, and download flows."""

    lesson_ids: tuple[str, ...] = ()
    title_match: str | None = None
    after_date: date | None = None
    before_date: date | None = None
    latest: int | None = None
    limit: int | None = None


@dataclass
class InspectOptions(SelectionOptions):
    """Options for listing lessons and assets without downloading media."""

    json_output: bool = False


@dataclass
class ProcessOptions(SelectionOptions):
    """Options for the end-to-end Echo360 transcript workflow."""

    output_root: Path = Path("swinydl-output")
    transcript_source: str = "auto"
    asr_backend: str = "auto"
    diarization_mode: str = "on"
    keep_audio: bool = False
    force: bool = False


@dataclass
class DownloadOptions(SelectionOptions):
    """Options for explicitly downloading Echo360 media artifacts."""

    output_root: Path = Path("swinydl-output")
    media: str = "audio"
    keep_audio: bool = False
    keep_video: bool = False
    force: bool = False


@dataclass
class TranscribeOptions:
    """Options for transcribing a local media or caption file."""

    output_root: Path = Path("swinydl-output")
    asr_backend: str = "auto"
    diarization_mode: str = "on"
    keep_audio: bool = False
    force: bool = False
    transcript_source: str = "asr"


@dataclass
class TranscriptWord:
    """A single word with timing and optional speaker attribution."""

    start: float
    end: float
    word: str
    speaker: str | None = None


@dataclass
class TranscriptSegment:
    """A sentence-like transcript segment with timing and optional speaker."""

    start: float
    end: float
    text: str
    speaker: str | None = None


@dataclass
class TranscriptArtifacts:
    """Filesystem locations for transcript artifacts emitted by a run."""

    txt_path: Path
    srt_path: Path
    json_path: Path
    audio_path: Path | None = None
    video_paths: list[Path] = field(default_factory=list)


@dataclass
class TranscriptResult:
    """Structured output for one processed lesson or local file."""

    status: str
    lesson: LessonManifest
    transcript_source: str
    asr_backend: str | None
    language: str | None
    diarized: bool
    model_name: str | None
    duration: float | None
    segments: list[TranscriptSegment]
    words: list[TranscriptWord]
    artifacts: TranscriptArtifacts
    error: str | None = None


@dataclass
class RunSummary:
    """Summary for a multi-lesson `inspect` or `process` execution."""

    run_id: str
    created_at: str
    command: str
    course: CourseManifest
    results: list[TranscriptResult]


@dataclass
class DownloadSummary:
    """Summary for a `download` execution and its emitted media files."""

    run_id: str
    created_at: str
    command: str
    course: CourseManifest
    downloads: list[dict[str, Any]]
