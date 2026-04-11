from __future__ import annotations

"""Thin `yt-dlp` wrapper used for authenticated Echo360 media retrieval."""

from pathlib import Path

from .auth import BrowserSession
from .echo_exceptions import DependencyMissingError, MediaResolutionError
from .models import LessonAsset, LessonManifest

AUDIO_EXTENSIONS = {"m4a", "aac", "mp3", "wav", "flac", "ogg"}


def select_caption_asset(lesson: LessonManifest) -> LessonAsset | None:
    """Return the first discovered native caption asset for a lesson."""
    for asset in lesson.assets:
        if asset.kind == "caption":
            return asset
    return None


def select_media_asset(lesson: LessonManifest, *, prefer_audio: bool) -> LessonAsset:
    """Choose the preferred downloadable lesson asset for the requested media mode."""
    if prefer_audio:
        for asset in lesson.assets:
            if asset.kind == "media" and asset.ext in AUDIO_EXTENSIONS:
                return asset
    for asset in lesson.assets:
        if asset.kind == "media":
            return asset
    raise MediaResolutionError(f"No downloadable media asset was found for lesson {lesson.lesson_id}.")


def download_with_ytdlp(
    browser: BrowserSession,
    url: str,
    destination: Path,
    *,
    media: str,
    file_stem: str,
) -> list[Path]:
    """Download one URL through `yt-dlp` using the current browser cookies."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:  # pragma: no cover - import depends on local env
        raise DependencyMissingError("Install yt-dlp to enable Echo360 media fetching.") from exc

    destination.mkdir(parents=True, exist_ok=True)
    cookie_file = browser.cookie_file()
    outtmpl = str(destination / f"{file_stem}.%(ext)s")
    before = {path.resolve() for path in destination.glob("*")}
    options = {
        "cookiefile": cookie_file,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": False,
        "overwrites": True,
        "format": "bestaudio/best" if media == "audio" else "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    }
    with YoutubeDL(options) as ydl:
        ydl.extract_info(url, download=True)
    after = [path.resolve() for path in destination.glob("*") if path.resolve() not in before]
    return sorted(after)


def download_lesson_media(
    browser: BrowserSession,
    lesson: LessonManifest,
    destination: Path,
    *,
    media: str,
    file_stem: str,
) -> list[Path]:
    """Download the requested lesson media artifacts into a destination directory."""
    asset = select_media_asset(lesson, prefer_audio=(media == "audio"))
    if media in {"audio", "video"}:
        return download_with_ytdlp(browser, asset.url, destination, media=media, file_stem=file_stem)

    downloads: list[Path] = []
    downloads.extend(
        download_with_ytdlp(browser, asset.url, destination, media="audio", file_stem=f"{file_stem}__audio")
    )
    downloads.extend(
        download_with_ytdlp(browser, asset.url, destination, media="video", file_stem=f"{file_stem}__video")
    )
    return downloads
