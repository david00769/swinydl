from __future__ import annotations

"""Small shared helpers for dates, filesystem output, slugs, and JSON export."""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from pathlib import Path
import json
import re
import unicodedata


def ensure_dir(path: Path) -> Path:
    """Create a directory tree and return the same path for chaining."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_date(value: str | None) -> date | None:
    """Parse a CLI date in `YYYY-MM-DD` form."""
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def now_utc() -> datetime:
    """Return a second-precision UTC timestamp for manifests."""
    return datetime.utcnow().replace(microsecond=0)


def slugify(value: str, max_length: int = 80) -> str:
    """Normalize arbitrary lesson or course titles into stable path slugs."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or "untitled")[:max_length].rstrip("-")


def lesson_key(date_string: str | None, lesson_id: str | None, index: int, title: str) -> str:
    """Build the canonical lesson key used for filenames and manifests."""
    date_token = date_string or "undated"
    lesson_token = lesson_id or str(index)
    return f"{date_token}__{lesson_token}__{slugify(title)}"


def media_extension(url: str) -> str | None:
    """Extract a likely file extension from a URL."""
    match = re.search(r"\.([a-zA-Z0-9]{2,5})(?:$|\?)", url)
    return match.group(1).lower() if match else None


def json_dumps(data: object) -> str:
    """Serialize JSON with deterministic formatting for user artifacts."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)


def export_dataclass(value: object) -> object:
    """Recursively convert dataclasses into JSON-serializable plain objects."""
    if is_dataclass(value):
        exported: dict[str, object] = {}
        for field in fields(value):
            if field.metadata.get("export", True) is False:
                continue
            exported[field.name] = export_dataclass(getattr(value, field.name))
        return exported
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat() + "Z"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [export_dataclass(item) for item in value]
    if isinstance(value, tuple):
        return [export_dataclass(item) for item in value]
    if isinstance(value, dict):
        return {key: export_dataclass(item) for key, item in value.items()}
    return value


def sort_lessons_newest_first(lessons: list[object], get_date) -> list[object]:
    """Sort lessons with dated items first, newest to oldest."""
    def sort_key(lesson: object) -> tuple[int, str]:
        lesson_date = get_date(lesson)
        if lesson_date is None:
            return (1, "")
        return (0, lesson_date)

    return sorted(lessons, key=sort_key, reverse=True)
