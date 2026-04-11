from __future__ import annotations

"""Friendly root entrypoint for `uv run app.py` usage."""

import re
import sys

from swinydl.auth import BrowserSession
from swinydl.echo_exceptions import Echo360Error
from swinydl.main import main


def _capture_course_url_from_browser() -> list[str]:
    """Launch Chrome, let the user navigate, then capture the current URL."""
    try:
        input(
            "Press [enter] to launch Chrome.\n"
            "Use that browser window to log in and open the Echo360 or Canvas page you want to process.\n"
        )
    except EOFError:
        return []

    try:
        with BrowserSession() as browser:
            value = browser.capture_course_url().strip()
    except Echo360Error as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return []
    return [value] if value else []


def run(argv: list[str] | None = None) -> int:
    """Run the CLI, capturing the course URL from Chrome when no arguments are supplied."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = _capture_course_url_from_browser()
        if not argv:
            print("Error: no usable course URL was captured.", file=sys.stderr)
            return 2
    return main(argv)


if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\\.pyw|\\.exe)?$", "", sys.argv[0])
    raise SystemExit(run())
