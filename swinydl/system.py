from __future__ import annotations

"""System-level helpers for local tools, SSL setup, and runtime diagnostics."""

import importlib.util
from pathlib import Path
import ssl
import shutil
import subprocess

import requests

COMMON_CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)

_TRUSTSTORE_CONFIGURED = False


def find_chrome_binary() -> str | None:
    """Return the preferred local Chrome or Chromium binary, if available."""
    for candidate in COMMON_CHROME_PATHS:
        if Path(candidate).exists():
            return candidate
    for candidate in ("google-chrome", "chromium", "chrome"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def find_swift_binary() -> str | None:
    """Return the `swift` executable on PATH, if present."""
    return shutil.which("swift")


def swift_version() -> str | None:
    """Return the installed Swift version string for diagnostics."""
    swift = find_swift_binary()
    if swift is None:
        return None
    try:
        completed = subprocess.run(
            [swift, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:  # pragma: no cover - depends on local swift toolchain
        return None
    first_line = completed.stdout.splitlines()[0] if completed.stdout else ""
    return first_line.strip() or None


def chrome_version() -> str | None:
    """Return the local Chrome or Chromium version string."""
    chrome_binary = find_chrome_binary()
    if chrome_binary is None:
        return None
    try:
        completed = subprocess.run(
            [chrome_binary, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:  # pragma: no cover - depends on local browser binary
        return None
    return completed.stdout.strip()


def configure_runtime_ssl() -> bool:
    """Inject the macOS trust store into Python SSL handling when available."""
    global _TRUSTSTORE_CONFIGURED
    if _TRUSTSTORE_CONFIGURED:
        return True
    if importlib.util.find_spec("truststore") is None:
        return False
    import truststore

    truststore.inject_into_ssl()
    _TRUSTSTORE_CONFIGURED = True
    return True


def ffmpeg_version() -> str | None:
    """Return the local ffmpeg version string for diagnostics."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    try:
        completed = subprocess.run(
            [ffmpeg, "-version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:  # pragma: no cover - depends on local ffmpeg install
        return None
    first_line = completed.stdout.splitlines()[0] if completed.stdout else ""
    return first_line.strip() or None


def https_error_hint(exc: Exception, *, service: str) -> str:
    """Convert low-level HTTPS failures into a user-facing troubleshooting hint."""
    if isinstance(exc, (requests.exceptions.SSLError, ssl.SSLError)):
        return (
            f"{service} failed TLS certificate verification. "
            "This Python runtime is not trusting the required certificate chain. "
            "Use the macOS system trust store via truststore, or configure SSL_CERT_FILE / REQUESTS_CA_BUNDLE."
        )
    if isinstance(exc, requests.exceptions.RequestException):
        return f"{service} failed: {exc}"
    return str(exc)
