"""Public package exports for the SWinyDL API."""

from .version import __version__
from .models import (
    CourseManifest,
    DownloadOptions,
    DownloadSummary,
    InspectOptions,
    LessonManifest,
    ProcessOptions,
    RunSummary,
    TranscriptResult,
    TranscribeOptions,
)
__all__ = [
    "CourseManifest",
    "DownloadOptions",
    "DownloadSummary",
    "InspectOptions",
    "LessonManifest",
    "ProcessOptions",
    "RunSummary",
    "TranscriptResult",
    "TranscribeOptions",
    "download_course",
    "inspect_course",
    "process_course",
    "transcribe_file",
]


def inspect_course(*args, **kwargs):
    """Import and invoke :func:`swinydl.workflow.inspect_course` lazily."""
    from .workflow import inspect_course as _inspect_course

    return _inspect_course(*args, **kwargs)


def process_course(*args, **kwargs):
    """Import and invoke :func:`swinydl.workflow.process_course` lazily."""
    from .workflow import process_course as _process_course

    return _process_course(*args, **kwargs)


def download_course(*args, **kwargs):
    """Import and invoke :func:`swinydl.workflow.download_course` lazily."""
    from .workflow import download_course as _download_course

    return _download_course(*args, **kwargs)


def transcribe_file(*args, **kwargs):
    """Import and invoke :func:`swinydl.workflow.transcribe_file` lazily."""
    from .workflow import transcribe_file as _transcribe_file

    return _transcribe_file(*args, **kwargs)
