"""Runtime health checks for local tools, staged models, and platform support."""

import importlib.util
import platform
from typing import Any

from .system import (
    chrome_version,
    configure_runtime_ssl,
    ffmpeg_version,
    find_chrome_binary,
    find_swift_binary,
    swift_version,
)
from .transcription import (
    diarization_runtime_status,
    diarizer_backend_available,
    diarizer_backend_status,
    parakeet_backend_available,
    parakeet_backend_status,
)
from .version import __version__


def doctor() -> dict[str, object]:
    """Collect a structured readiness report for the local runtime."""
    truststore_enabled = configure_runtime_ssl()
    python_version = platform.python_version()
    machine = platform.machine()
    env = {
        "version": __version__,
        "python": python_version,
        "platform": platform.platform(),
        "machine": machine,
        "swift_binary": find_swift_binary(),
        "swift_version": swift_version(),
        "chrome_binary": find_chrome_binary(),
        "chrome_version": chrome_version(),
        "ffmpeg_version": ffmpeg_version(),
        "truststore_enabled": truststore_enabled,
    }

    checks = [
        _check_python(python_version),
        _check_platform(machine),
        _check_swift(env),
        _check_chrome(env),
        _check_ffmpeg(env),
        _check_ssl(env),
        _check_package("selenium", required=True, message="Selenium is installed."),
        _check_package("yt_dlp", required=True, message="yt-dlp is installed."),
        _check_asr_backend_parakeet(),
        _check_diarization_backend(),
    ]
    summary = _summarize_checks(checks)
    return {
        "summary": summary,
        "checks": checks,
        "environment": env,
    }


def format_doctor_report(report: dict[str, object]) -> str:
    """Render the structured doctor report into a human-readable summary."""
    summary = report["summary"]
    lines = [
        f"Doctor summary: {summary['pass']} pass, {summary['warn']} warn, {summary['fail']} fail",
    ]
    for check in report["checks"]:
        lines.append(
            f"{check['status'].upper():4} {check['id']}: {check['summary']}"
        )
        if check.get("fix"):
            lines.append(f"      fix: {check['fix']}")
    return "\n".join(lines)


def _check_python(python_version: str) -> dict[str, object]:
    supported = tuple(int(part) for part in python_version.split(".")[:2]) >= (3, 11)
    return _check(
        "python",
        "pass" if supported else "fail",
        f"Python {python_version}" if supported else f"Python {python_version} is below the supported floor.",
        fix="Use Python 3.11 or newer." if not supported else None,
    )


def _check_platform(machine: str) -> dict[str, object]:
    supported = platform.system() == "Darwin" and machine == "arm64"
    return _check(
        "platform",
        "pass" if supported else "warn",
        "Running on macOS Apple Silicon." if supported else "This project is only validated on macOS Apple Silicon.",
        fix="Use a macOS Apple Silicon machine for the supported v4 runtime." if not supported else None,
    )


def _check_chrome(env: dict[str, object]) -> dict[str, object]:
    chrome_binary = env["chrome_binary"]
    if chrome_binary:
        return _check("chrome", "pass", f"Chrome available at {chrome_binary}.")
    return _check(
        "chrome",
        "fail",
        "Chrome or Chromium was not found.",
        fix="Install Google Chrome or Chromium so Selenium can reuse a persistent browser profile.",
    )


def _check_swift(env: dict[str, object]) -> dict[str, object]:
    swift_binary = env["swift_binary"]
    if swift_binary:
        version = env["swift_version"] or "Swift is installed."
        return _check("swift", "pass", version)
    return _check(
        "swift",
        "fail",
        "Swift was not found on PATH.",
        fix="Install Xcode command line tools so the Parakeet CoreML runner can be built locally.",
    )


def _check_ffmpeg(env: dict[str, object]) -> dict[str, object]:
    version = env["ffmpeg_version"]
    if version:
        return _check("ffmpeg", "pass", version)
    return _check(
        "ffmpeg",
        "fail",
        "ffmpeg was not found on PATH.",
        fix="Install ffmpeg and ensure it is available on PATH.",
    )


def _check_ssl(env: dict[str, object]) -> dict[str, object]:
    if env["truststore_enabled"]:
        return _check("ssl", "pass", "macOS system trust store is active.")
    return _check(
        "ssl",
        "warn",
        "truststore is not active; HTTPS may rely on certifi only.",
        fix="Install truststore and let the app inject the macOS system trust store.",
    )


def _check_package(name: str, *, required: bool, message: str) -> dict[str, object]:
    """Validate whether an importable package is present in the active environment."""
    installed = importlib.util.find_spec(name) is not None
    if installed:
        return _check(name, "pass", message)
    status = "fail" if required else "warn"
    fix = f"Install the '{name}' dependency." if required else f"Install the optional '{name}' dependency to enable this feature."
    return _check(name, status, f"{name} is not installed.", fix=fix)


def _check_asr_backend_parakeet() -> dict[str, object]:
    """Report whether the local Parakeet CoreML runner can be used."""
    status = parakeet_backend_status()
    if parakeet_backend_available():
        return _check(
            "asr-backend-parakeet",
            "pass",
            f"Parakeet CoreML backend is available at {status['model_dir']}.",
        )
    return _check(
        "asr-backend-parakeet",
        "fail",
        "Parakeet CoreML backend is not ready.",
        fix=str(status["reason"]),
        details={"model_dir": status["model_dir"]},
    )


def _check_diarization_backend() -> dict[str, object]:
    """Report whether the local CoreML diarization runner can be used."""
    status = diarizer_backend_status()
    ready, reason = diarization_runtime_status(require_token=False)
    if diarizer_backend_available() and ready:
        return _check(
            "diarization-backend-coreml",
            "pass",
            f"Local CoreML diarization backend is available at {status['model_dir']}.",
        )
    return _check(
        "diarization-backend-coreml",
        "fail",
        "Local CoreML diarization backend is not ready.",
        fix=reason or str(status["reason"]),
        details={"model_dir": status["model_dir"]},
    )


def _summarize_checks(checks: list[dict[str, object]]) -> dict[str, int | bool]:
    """Aggregate pass, warn, and fail counts for the doctor report."""
    counts = {
        "pass": sum(1 for check in checks if check["status"] == "pass"),
        "warn": sum(1 for check in checks if check["status"] == "warn"),
        "fail": sum(1 for check in checks if check["status"] == "fail"),
    }
    counts["ready"] = counts["fail"] == 0
    return counts


def _check(
    check_id: str,
    status: str,
    summary: str,
    *,
    fix: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build a single doctor check payload."""
    payload: dict[str, object] = {
        "id": check_id,
        "status": status,
        "summary": summary,
    }
    if fix:
        payload["fix"] = fix
    if details:
        payload["details"] = details
    return payload


def _short_error(message: str) -> str:
    """Collapse long exception text into a short single-line diagnostic."""
    first_line = message.strip().splitlines()[0] if message.strip() else "Unknown error"
    return first_line[:240]
