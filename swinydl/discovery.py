from __future__ import annotations

"""Echo360 course discovery, lesson normalization, and asset inspection."""

from dataclasses import replace
from pathlib import Path
import json
import re
from typing import Any

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .auth import BrowserSession
from .echo_exceptions import DiscoveryError
from .models import CourseManifest, LessonAsset, LessonManifest, SelectionOptions
from .system import configure_runtime_ssl, https_error_hint
from .utils import media_extension, parse_date

DEFAULT_CLASSIC_HOST = "https://view.streaming.sydney.edu.au:8443"
CAPTION_EXTENSIONS = {"vtt", "srt"}
MEDIA_EXTENSIONS = {"m3u8", "mp4", "m4a", "aac", "mp3", "mov", "webm"}


def extract_course_hostname(course_url: str) -> str | None:
    """Extract the scheme and host from a full Echo360 course URL."""
    match = re.search(r"https?://[^/]*", course_url)
    return match.group() if match else None


def is_echo360_cloud_host(course_hostname: str | None) -> bool:
    """Return whether a hostname points at the cloud Echo360 product."""
    if course_hostname is None:
        return False
    return any(token in course_hostname for token in ("echo360.org", "echo360.net"))


def extract_course_uuid(course_url: str, using_echo360_cloud: bool) -> str:
    """Extract the course identifier used by the classic or cloud endpoints."""
    pattern = (
        r"[^/]([0-9a-zA-Z]+[-])+[0-9a-zA-Z]+"
        if using_echo360_cloud
        else r"[^/]+(?=/$|$)"
    )
    match = re.search(pattern, course_url)
    if match is None:
        raise ValueError("Unable to parse a course identifier from the supplied Echo360 URL.")
    return match.group()


def inspect_course(course_url: str, browser: BrowserSession) -> CourseManifest:
    """Discover course metadata and lessons from an authenticated Echo360 session."""
    configure_runtime_ssl()
    hostname = extract_course_hostname(course_url) or DEFAULT_CLASSIC_HOST
    platform = "cloud" if is_echo360_cloud_host(hostname) else "classic"
    course_uuid = extract_course_uuid(course_url, using_echo360_cloud=(platform == "cloud"))
    full_course_url = (
        course_url
        if extract_course_hostname(course_url)
        else f"{hostname}/ess/portal/section/{course_uuid}"
    )
    browser.ensure_access(full_course_url)
    session = browser.requests_session()

    if platform == "cloud":
        payload = _fetch_json(session, f"{hostname}/section/{course_uuid}/syllabus")
        lessons, course_title = _parse_cloud_lessons(hostname, payload)
        course_id = None
    else:
        endpoint = f"{hostname}/ess/client/api/sections/{course_uuid}/section-data.json?pageSize=100"
        payload = _fetch_json(session, endpoint)
        lessons, course_id, course_title = _parse_classic_lessons(payload)

    return CourseManifest(
        source_url=full_course_url,
        hostname=hostname,
        platform=platform,
        course_uuid=course_uuid,
        course_id=course_id,
        course_title=course_title,
        lessons=lessons,
    )


def filter_lessons(course: CourseManifest, options: SelectionOptions) -> CourseManifest:
    """Apply CLI-style lesson filters and ordering to a discovered course."""
    lessons = list(course.lessons)
    if options.lesson_ids:
        wanted = {lesson_id.lower() for lesson_id in options.lesson_ids}
        lessons = [lesson for lesson in lessons if lesson.lesson_id.lower() in wanted]
    if options.title_match:
        token = options.title_match.lower()
        lessons = [lesson for lesson in lessons if token in lesson.title.lower()]
    if options.after_date:
        lessons = [
            lesson
            for lesson in lessons
            if lesson.date and parse_date(lesson.date) and parse_date(lesson.date) >= options.after_date
        ]
    if options.before_date:
        lessons = [
            lesson
            for lesson in lessons
            if lesson.date and parse_date(lesson.date) and parse_date(lesson.date) <= options.before_date
        ]
    lessons.sort(key=lambda lesson: (lesson.date is not None, lesson.date or ""), reverse=True)
    if options.latest is not None:
        lessons = lessons[: options.latest]
    if options.limit is not None:
        lessons = lessons[: options.limit]
    return replace(course, lessons=lessons)


def resolve_lesson_assets(browser: BrowserSession, lesson: LessonManifest) -> LessonManifest:
    """Open a lesson page and add any `<video>` or `<track>` assets found there."""
    assert browser.driver is not None
    assets: list[LessonAsset] = list(lesson.assets)
    browser.driver.get(lesson.lesson_url)
    try:
        video = WebDriverWait(browser.driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        src = video.get_attribute("src")
        if src:
            assets.append(LessonAsset(kind="media", url=src, label="page-video", ext=media_extension(src)))
        for track in video.find_elements(By.TAG_NAME, "track"):
            track_src = track.get_attribute("src")
            if track_src:
                assets.append(
                    LessonAsset(
                        kind="caption",
                        url=track_src,
                        label=track.get_attribute("label") or track.get_attribute("kind"),
                        ext=media_extension(track_src),
                    )
                )
    except Exception:
        pass
    return replace(lesson, assets=_dedupe_assets(assets))


def _fetch_json(session: requests.Session, url: str) -> dict[str, Any]:
    """Fetch JSON from Echo360 and normalize network and parse failures."""
    try:
        response = session.get(url, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise DiscoveryError(https_error_hint(exc, service=f"Echo360 request to {url}")) from exc
    if not response.ok:
        raise DiscoveryError(f"Echo360 request failed for {url} with status {response.status_code}.")
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise DiscoveryError(f"Echo360 returned non-JSON content for {url}.") from exc


def _parse_classic_lessons(payload: dict[str, Any]) -> tuple[list[LessonManifest], str | None, str]:
    """Normalize classic Echo360 section JSON into lesson manifests."""
    section = payload.get("section", {})
    course = section.get("course", {})
    presentations = section.get("presentations", {}).get("pageContents", [])
    lessons: list[LessonManifest] = []
    for index, item in enumerate(presentations, start=1):
        lesson_id = _extract_lesson_id(item.get("richMedia")) or f"classic-{index}"
        lessons.append(
            LessonManifest(
                lesson_id=lesson_id,
                title=item.get("title") or f"Lesson {index}",
                date=_normalize_date(item.get("startTime")),
                lesson_url=item.get("richMedia") or "",
                index=index,
                assets=_detect_assets(item),
                source_payload=item,
            )
        )
    return lessons, course.get("identifier"), course.get("name") or "Untitled Course"


def _parse_cloud_lessons(hostname: str, payload: dict[str, Any]) -> tuple[list[LessonManifest], str]:
    """Normalize cloud Echo360 syllabus JSON into lesson manifests."""
    lessons: list[LessonManifest] = []
    course_title = "Untitled Course"
    for index, item in enumerate(payload.get("data", []), start=1):
        if "lessons" in item:
            group_name = item.get("groupInfo", {}).get("name") or f"Group {index}"
            for sub_index, sub_item in enumerate(item["lessons"], start=1):
                lesson = _build_cloud_lesson(
                    hostname,
                    sub_item,
                    index=index * 100 + sub_index,
                    title_prefix=f"{group_name} - ",
                )
                lessons.append(lesson)
                course_title = course_title if course_title != "Untitled Course" else _extract_cloud_course_title(sub_item)
        else:
            lesson = _build_cloud_lesson(hostname, item, index=index)
            lessons.append(lesson)
            course_title = course_title if course_title != "Untitled Course" else _extract_cloud_course_title(item)
    return lessons, course_title


def _build_cloud_lesson(
    hostname: str,
    item: dict[str, Any],
    *,
    index: int,
    title_prefix: str = "",
) -> LessonManifest:
    """Build one normalized lesson manifest from a cloud syllabus item."""
    lesson_node = item.get("lesson", {}).get("lesson", {})
    lesson_id = str(lesson_node.get("id") or f"cloud-{index}")
    lesson_title = title_prefix + (lesson_node.get("name") or f"Lesson {index}")
    lesson_url = f"{hostname}/lesson/{lesson_id}/classroom"
    return LessonManifest(
        lesson_id=lesson_id,
        title=lesson_title,
        date=_normalize_date(
            item.get("lesson", {}).get("startTimeUTC")
            or lesson_node.get("createdAt")
            or item.get("groupInfo", {}).get("createdAt")
        ),
        lesson_url=lesson_url,
        index=index,
        assets=_detect_assets(item),
        source_payload=item,
    )


def _extract_cloud_course_title(item: dict[str, Any]) -> str:
    """Extract the course title from one cloud syllabus lesson payload."""
    return (
        item.get("lesson", {})
        .get("video", {})
        .get("published", {})
        .get("courseName")
        or "Untitled Course"
    )


def _extract_lesson_id(url: str | None) -> str | None:
    """Extract a stable lesson-like identifier from a URL when possible."""
    if not url:
        return None
    match = re.search(r"([0-9a-zA-Z]{8,}(?:-[0-9a-zA-Z]{4,})+)", url)
    return match.group(1) if match else None


def _normalize_date(value: str | None) -> str | None:
    """Reduce various Echo360 timestamps to `YYYY-MM-DD`."""
    if not value:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", value)
    return match.group(1) if match else None


def _detect_assets(payload: dict[str, Any]) -> list[LessonAsset]:
    """Walk nested JSON and collect obvious media and caption URLs."""
    assets: list[LessonAsset] = []

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else key)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
            return
        if not isinstance(value, str) or not value.startswith("http"):
            return
        ext = media_extension(value)
        label = path or None
        path_lower = path.lower()
        if ext in CAPTION_EXTENSIONS or any(token in path_lower for token in ("caption", "subtitle", "transcript")):
            assets.append(LessonAsset(kind="caption", url=value, label=label, ext=ext))
        elif ext in MEDIA_EXTENSIONS:
            assets.append(LessonAsset(kind="media", url=value, label=label, ext=ext))

    walk(payload)
    return _dedupe_assets(assets)


def _dedupe_assets(assets: list[LessonAsset]) -> list[LessonAsset]:
    """Keep the first asset for each `(kind, url)` pair."""
    seen: set[tuple[str, str]] = set()
    deduped: list[LessonAsset] = []
    for asset in assets:
        key = (asset.kind, asset.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(asset)
    return deduped
