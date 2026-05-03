from __future__ import annotations

"""Authenticated session providers for browser-backed and manifest-backed runs."""

from contextlib import suppress
from dataclasses import asdict
from http.cookiejar import MozillaCookieJar
from pathlib import Path
import time
import uuid

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from .app_paths import browser_profile_dir, ensure_runtime_dirs, logs_dir, temp_dir
from .echo_exceptions import BrowserSetupError
from .models import BrowserCookie
from .system import find_chrome_binary


class AuthenticatedSession:
    """Interface for a session provider that can back HTTP and yt-dlp access."""

    driver = None

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


class BrowserSession(AuthenticatedSession):
    """Manage the legacy Chrome fallback session and expose authenticated cookies."""

    def __init__(self, *, course_url: str | None = None) -> None:
        ensure_runtime_dirs()
        self.course_url = course_url
        self.driver: webdriver.Chrome | None = None

    def __enter__(self) -> "BrowserSession":
        chrome_binary = find_chrome_binary()
        if chrome_binary is None:
            raise BrowserSetupError("Chrome or Chromium was not found on this Mac.")

        log_path = logs_dir() / "selenium.log"
        options = Options()
        options.binary_location = chrome_binary
        options.add_argument(f"--user-data-dir={browser_profile_dir()}")
        options.add_argument("--window-size=1600,1200")
        service = Service(log_output=str(log_path))

        try:
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as exc:  # pragma: no cover - depends on local browser state
            raise BrowserSetupError(f"Failed to start Chrome automation: {exc}") from exc
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.driver is not None:
            with suppress(Exception):
                self.driver.quit()

    def ensure_access(self, url: str) -> None:
        """Open a page and pause for manual login if Echo360 redirects to SSO."""
        assert self.driver is not None
        self.driver.get(url)
        time.sleep(1.5)
        if self._looks_like_login_page():
            print("Echo360 needs an interactive login in Chrome.")
            input("> Complete the login in the browser, then press [enter] to continue\n")
            self.driver.get(url)
            time.sleep(1.5)

    def capture_course_url(self) -> str:
        """Let the user navigate in the browser, then capture the current URL."""
        assert self.driver is not None
        self.driver.get(self.course_url or "about:blank")
        print("Chrome opened with your persistent profile.")
        print("Log in if needed, then navigate to the course or lecture page you want to process.")
        print("The app will capture the current browser URL when you continue.")
        input("> When Chrome is on the right page, press [enter] here to continue\n")
        time.sleep(0.5)

        current_url = (self.driver.current_url or "").strip()
        if not current_url or current_url in {"about:blank", "data:,"}:
            raise BrowserSetupError("No usable URL was captured from Chrome.")
        if self._looks_like_login_page():
            raise BrowserSetupError(
                "Chrome is still on a login page. Finish login and navigate to the target page before continuing."
            )
        return current_url

    def requests_session(self) -> requests.Session:
        """Build a `requests.Session` populated with the current browser cookies."""
        assert self.driver is not None
        session = requests.Session()
        for cookie in self.driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])
        return session

    def cookie_file(self) -> str:
        """Write browser cookies to a Netscape-format file for `yt-dlp`."""
        assert self.driver is not None
        cookie_path = _cookie_file_path()
        jar = MozillaCookieJar(str(cookie_path))
        for cookie in self.driver.get_cookies():
            domain = cookie.get("domain", "")
            path = cookie.get("path", "/")
            secure = bool(cookie.get("secure", False))
            expires = cookie.get("expiry")
            jar.set_cookie(
                requests.cookies.create_cookie(
                    domain=domain,
                    name=cookie["name"],
                    value=cookie["value"],
                    path=path,
                    secure=secure,
                    expires=expires,
                )
            )
        jar.save(ignore_discard=True, ignore_expires=True)
        return str(cookie_path)

    def _looks_like_login_page(self) -> bool:
        """Heuristically detect an Echo360 or institution login page."""
        assert self.driver is not None
        current_url = self.driver.current_url.lower()
        page = self.driver.page_source.lower()
        if any(token in current_url for token in ("login", "sso", "auth")):
            return True
        return all(token in page for token in ("password", "username"))


class CookieSession(AuthenticatedSession):
    """Use pre-exported browser cookies without launching a local browser."""

    def __init__(self, cookies: list[BrowserCookie]) -> None:
        ensure_runtime_dirs()
        self.cookies = list(cookies)

    def requests_session(self) -> requests.Session:
        """Build a requests session populated from exported browser cookies."""
        session = requests.Session()
        for cookie in self.cookies:
            session.cookies.set(
                cookie.name,
                cookie.value,
                domain=cookie.domain,
                path=cookie.path,
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


def _cookie_file_path() -> Path:
    directory = temp_dir() / "cookies"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"swinydl-cookies-{uuid.uuid4().hex}.txt"
