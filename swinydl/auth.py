from __future__ import annotations

"""Cookie-backed sessions for Echo360 access.

Jobs launched from Safari carry the cookies the extension exported. The CLI loads
cookies from a Netscape cookie file or reads them from a local browser through
yt-dlp. No browser is automated.
"""

from dataclasses import asdict
from http.cookiejar import CookieJar, MozillaCookieJar
from pathlib import Path
from urllib.parse import urlsplit
import time
import uuid

import requests

from .app_paths import ensure_runtime_dirs, temp_dir
from .echo_exceptions import CookieSourceError
from .models import BrowserCookie

SUPPORTED_COOKIE_BROWSERS = ("safari", "chrome", "chromium", "firefox", "edge", "brave")


class AuthenticatedSession:
    """Interface for a session provider that can back HTTP and yt-dlp access."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def ensure_access(self, url: str) -> None:
        """Ensure the provided URL is reachable in the authenticated context."""

    def requests_session(self) -> requests.Session:
        """Return a requests session carrying the current authenticated cookies."""
        raise NotImplementedError

    def cookie_file(self) -> str:
        """Return a Netscape-format cookie file path for downstream tools."""
        raise NotImplementedError


class CookieSession(AuthenticatedSession):
    """Use pre-exported browser cookies without launching a local browser."""

    def __init__(self, cookies: list[BrowserCookie]) -> None:
        ensure_runtime_dirs()
        self.cookies = list(cookies)

    def requests_session(self) -> requests.Session:
        """Build a requests session populated from exported browser cookies."""
        session = requests.Session()
        for cookie in self.cookies:
            # secure=True keeps an https-only session cookie off any http:// request.
            session.cookies.set_cookie(
                requests.cookies.create_cookie(
                    name=cookie.name,
                    value=cookie.value,
                    domain=cookie.domain,
                    path=cookie.path,
                    secure=cookie.secure,
                    expires=cookie.expiry,
                )
            )
        return session

    def cookie_file(self) -> str:
        """Write exported cookies to a Netscape-format file for yt-dlp."""
        cookie_path = _cookie_file_path()
        jar = MozillaCookieJar(str(cookie_path))
        for cookie in self.cookies:
            payload = asdict(cookie)
            jar.set_cookie(
                requests.cookies.create_cookie(
                    domain=payload["domain"],
                    name=payload["name"],
                    value=payload["value"],
                    path=payload["path"],
                    secure=payload["secure"],
                    expires=payload["expiry"],
                    rest={
                        "HttpOnly": payload["http_only"],
                        "SameSite": payload["same_site"] or "",
                    },
                )
            )
        jar.save(ignore_discard=True, ignore_expires=True)
        return str(cookie_path)


def course_session(
    course_url: str,
    *,
    cookies_file: Path | str | None = None,
    cookies_from_browser: str | None = None,
) -> CookieSession:
    """Build a cookie session for a CLI course command from exactly one cookie source."""
    if bool(cookies_file) == bool(cookies_from_browser):
        raise CookieSourceError(
            "Course commands need Echo360 cookies: pass --cookies-from-browser safari "
            "(or chrome, firefox, ...) after logging in there, or --cookies with a "
            "Netscape cookies.txt file. Jobs launched from the Safari extension carry "
            "their own cookies."
        )
    if cookies_file:
        cookies = cookies_from_file(cookies_file)
        source = str(cookies_file)
    else:
        cookies = cookies_from_browser_store(str(cookies_from_browser))
        source = f"the {cookies_from_browser} cookie store"
    if not urlsplit(course_url).hostname:
        raise CookieSourceError(
            f"{course_url!r} is not a full course URL. Pass the https:// address of the "
            "Echo360 course page, so SWinyDL knows which site's cookies to use."
        )
    scoped = cookies_for_url(cookies, course_url)
    if not scoped:
        raise CookieSourceError(
            f"No current cookies for {urlsplit(course_url).hostname} were found in {source}. "
            "Log in to the course in that browser (again, if the session expired), then run the command again."
        )
    return CookieSession(scoped)


def cookies_from_file(path: Path | str) -> list[BrowserCookie]:
    """Load a Netscape-format cookies.txt file."""
    jar = MozillaCookieJar(str(path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except (OSError, ValueError) as exc:
        raise CookieSourceError(f"Could not read the cookie file {path}: {exc}") from exc
    return _cookies_from_jar(jar)


def cookies_from_browser_store(browser: str) -> list[BrowserCookie]:
    """Read cookies from a local browser's cookie store through yt-dlp."""
    name = browser.strip().lower()
    if name not in SUPPORTED_COOKIE_BROWSERS:
        raise CookieSourceError(
            f"Unsupported browser {browser!r}. Choose one of: {', '.join(SUPPORTED_COOKIE_BROWSERS)}."
        )
    try:
        from yt_dlp.cookies import extract_cookies_from_browser
    except ImportError as exc:  # pragma: no cover - yt-dlp is a declared dependency
        raise CookieSourceError("yt-dlp is required to read browser cookies.") from exc
    try:
        jar = extract_cookies_from_browser(name)
    except Exception as exc:  # yt-dlp raises plain errors for locked or unreadable stores
        hint = (
            " Safari's cookie store needs Full Disk Access for the app running this command "
            "(System Settings > Privacy & Security > Full Disk Access)."
            if name == "safari"
            else ""
        )
        raise CookieSourceError(f"Could not read {name} cookies: {exc}.{hint}") from exc
    return _cookies_from_jar(jar)


def cookies_for_url(cookies: list[BrowserCookie], url: str) -> list[BrowserCookie]:
    """Keep the cookies a browser would send to ``url``'s host (its own and parent domains).

    A browser cookie store holds every site's cookies; only the course host's belong in a job.
    """
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return []
    now = time.time()
    kept: list[BrowserCookie] = []
    for cookie in cookies:
        if cookie.expiry and cookie.expiry < now:
            continue  # a browser would not send it either
        domain = cookie.domain.lower().lstrip(".")
        if domain and (host == domain or host.endswith(f".{domain}")):
            kept.append(cookie)
    return kept


def _cookies_from_jar(jar: CookieJar) -> list[BrowserCookie]:
    cookies: list[BrowserCookie] = []
    for cookie in jar:
        rest = getattr(cookie, "_rest", {}) or {}
        cookies.append(
            BrowserCookie(
                name=cookie.name,
                value=cookie.value or "",
                domain=cookie.domain,
                path=cookie.path or "/",
                secure=bool(cookie.secure),
                http_only=any(key.lower() == "httponly" for key in rest),
                expiry=int(cookie.expires) if cookie.expires else None,
            )
        )
    return cookies


def _cookie_file_path() -> Path:
    directory = temp_dir() / "cookies"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"swinydl-cookies-{uuid.uuid4().hex}.txt"
