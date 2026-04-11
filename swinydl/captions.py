from __future__ import annotations

"""Fetch, parse, and emit caption formats used by Echo360 workflows."""

from pathlib import Path
import re

import requests

from .echo_exceptions import NativeCaptionError
from .models import TranscriptSegment
from .system import configure_runtime_ssl, https_error_hint
from .utils import media_extension


TIMESTAMP_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[.,]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[.,]\d{3})"
)


def load_native_caption_segments(session: requests.Session, url: str) -> list[TranscriptSegment]:
    """Download a native caption file and parse it into transcript segments."""
    configure_runtime_ssl()
    try:
        response = session.get(url, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise NativeCaptionError(https_error_hint(exc, service=f"Caption download from {url}")) from exc
    if not response.ok:
        raise NativeCaptionError(f"Failed to retrieve native captions from {url}.")
    ext = media_extension(url)
    text = response.text
    if ext == "srt":
        return parse_srt(text)
    return parse_webvtt(text)


def parse_webvtt(text: str) -> list[TranscriptSegment]:
    """Parse a WebVTT payload into normalized transcript segments."""
    lines = text.splitlines()
    segments: list[TranscriptSegment] = []
    buffer: list[str] = []
    start = end = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == "WEBVTT":
            if start is not None and buffer:
                segments.append(
                    TranscriptSegment(
                        start=_parse_timestamp(start),
                        end=_parse_timestamp(end),
                        text=" ".join(buffer).strip(),
                    )
                )
                buffer = []
                start = end = None
            continue
        match = TIMESTAMP_PATTERN.match(stripped)
        if match:
            start = match.group("start")
            end = match.group("end")
            continue
        if stripped.isdigit() and start is None:
            continue
        buffer.append(_strip_voice_tag(stripped))
    if start is not None and buffer:
        segments.append(
            TranscriptSegment(
                start=_parse_timestamp(start),
                end=_parse_timestamp(end),
                text=" ".join(buffer).strip(),
            )
        )
    if not segments:
        raise NativeCaptionError("No caption segments could be parsed from the native subtitle file.")
    return segments


def parse_srt(text: str) -> list[TranscriptSegment]:
    """Parse an SRT payload into normalized transcript segments."""
    return parse_webvtt(text.replace(",", "."))


def segments_to_text(segments: list[TranscriptSegment]) -> str:
    """Render segments as plain transcript text."""
    return "\n".join(segment.text for segment in segments)


def segments_to_srt(segments: list[TranscriptSegment]) -> str:
    """Render segments as SRT, preserving speaker labels when available."""
    chunks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        chunks.append(str(index))
        chunks.append(
            f"{_format_timestamp(segment.start)} --> {_format_timestamp(segment.end)}"
        )
        prefix = f"[{segment.speaker}] " if segment.speaker else ""
        chunks.append(prefix + segment.text)
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def _parse_timestamp(value: str) -> float:
    """Convert a caption timestamp string to seconds."""
    parts = re.split(r"[:.,]", value)
    if len(parts) != 4:
        raise NativeCaptionError(f"Unsupported caption timestamp: {value}")
    hours, minutes, seconds, milliseconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def _format_timestamp(value: float) -> str:
    """Convert seconds to an SRT timestamp string."""
    total_ms = int(round(value * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _strip_voice_tag(text: str) -> str:
    """Remove simple WebVTT voice tags from caption text."""
    return re.sub(r"<v[^>]*>", "", text).replace("</v>", "").strip()
