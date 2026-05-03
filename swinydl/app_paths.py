from __future__ import annotations

"""Runtime paths used for browser state, logs, caches, and outputs."""

from pathlib import Path

APP_NAME = "swinydl"


def app_support_dir() -> Path:
    """Return the app support root under the user's Library directory."""
    return Path.home() / "Library" / "Application Support" / APP_NAME


def browser_profile_dir() -> Path:
    """Return the persistent Chrome profile used for Echo360 sessions."""
    return app_support_dir() / "browser-profile"


def logs_dir() -> Path:
    """Return the directory used for Selenium and runtime logs."""
    return app_support_dir() / "logs"


def cache_dir() -> Path:
    """Return the package-local directory used for temporary downloads and run caches."""
    return temp_dir()


def temp_dir() -> Path:
    """Return the package-local temp directory for runtime scratch files."""
    return Path.cwd() / "temp"


def default_output_root() -> Path:
    """Return the default output directory in the current working tree."""
    return Path.cwd() / "swinydl-output"


def ensure_runtime_dirs() -> None:
    """Create the runtime directories needed by the app if they do not exist."""
    for directory in (app_support_dir(), browser_profile_dir(), logs_dir(), cache_dir()):
        directory.mkdir(parents=True, exist_ok=True)
