from __future__ import annotations

"""Fetch, parse, and emit caption formats used by Echo360 workflows."""

import html
import re

import requests

from .echo_exceptions import NativeCaptionError
from .models import TranscriptSegment
from .system import configure_runtime_ssl, https_error_hint
from .utils import media_extension


TIMESTAMP_PATTERN = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{3})"
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
    # WebVTT is always UTF-8; requests would guess ISO-8859-1 for text/* without a charset.
    text = response.content.decode("utf-8-sig", errors="replace")
    if ext == "srt":
        return parse_srt(text)
    return parse_webvtt(text)


def parse_webvtt(text: str) -> list[TranscriptSegment]:
    """Parse a WebVTT payload into normalized transcript segments."""
    lines = text.lstrip("\ufeff").splitlines()
    segments: list[TranscriptSegment] = []
    buffer: list[str] = []
    start = end = None
    for position, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("WEBVTT"):
            if start is None or not buffer:
                # Text outside a cue (header metadata, NOTE/STYLE/REGION blocks, cue ids),
                # or a cue with no text: either way nothing to keep, and the cue is closed.
                buffer = []
                start = end = None
                continue
            if buffer:
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
            if start is None:
                buffer = []  # a cue identifier line, not caption text
            elif buffer:
                # Flush a cue that was not terminated by a blank line before
                # starting the next one, so adjacent cues do not merge.
                segments.append(
                    TranscriptSegment(
                        start=_parse_timestamp(start),
                        end=_parse_timestamp(end),
                        text=" ".join(buffer).strip(),
                    )
                )
                buffer = []
            start = match.group("start")
            end = match.group("end")
            continue
        if stripped.isdigit() and (start is None or _next_is_timestamp(lines, position)):
            # An SRT cue number. Without a blank line between cues it follows the
            # previous cue's text, so it is recognised by the timestamp after it.
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
    """Parse an SRT payload into normalized transcript segments.

    SRT uses a comma as the timestamp decimal separator. The shared parser and
    ``_parse_timestamp`` already accept both ``,`` and ``.`` in timestamps, so
    the payload is passed through unchanged to avoid corrupting commas that
    appear inside the spoken caption text.
    """
    return parse_webvtt(text)


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


def _next_is_timestamp(lines: list[str], position: int) -> bool:
    """Whether the line after ``position`` is a cue timing line."""
    following = position + 1
    return following < len(lines) and TIMESTAMP_PATTERN.match(lines[following].strip()) is not None


def _parse_timestamp(value: str) -> float:
    """Convert a caption timestamp string to seconds."""
    parts = re.split(r"[:.,]", value)
    if len(parts) == 4:
        hours, minutes, seconds, milliseconds = parts
    elif len(parts) == 3:
        # WebVTT permits the hours field to be omitted (MM:SS.mmm).
        hours = "0"
        minutes, seconds, milliseconds = parts
    else:
        raise NativeCaptionError(f"Unsupported caption timestamp: {value}")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def _format_timestamp(value: float) -> str:
    """Convert seconds to an SRT timestamp string."""
    total_ms = int(round(value * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


CAPTION_TAG_PATTERN = re.compile(r"</?(?:v|c|i|b|u|ruby|rt|lang|font)\b[^>]*>|<\d[\d:.]*>", re.IGNORECASE)


def _strip_voice_tag(text: str) -> str:
    """Remove WebVTT/SRT markup (voice, class, i/b/u, ruby, lang, font, timestamps) and decode entities.

    Only caption tags are removed, so a literal "a < b" in the text survives.
    """
    return re.sub(r"\s{2,}", " ", html.unescape(CAPTION_TAG_PATTERN.sub("", text))).strip()
