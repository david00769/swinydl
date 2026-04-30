"""Runtime health checks for local tools, staged models, and platform support."""

import importlib.util
from pathlib import Path
import platform
from typing import Any

from .system import (
    chrome_version,
    configure_runtime_ssl,
    ffmpeg_version,
    find_chrome_binary,
    find_swift_binary,
    find_xcodebuild_binary,
    find_xcodegen_binary,
    safari_built_app_path,
    safari_extension_bundle_path,
    safari_project_path,
    safari_project_spec_path,
    swift_version,
    xcode_first_launch_ready,
    xcode_select_path,
)
from .transcription import (
    diarization_runtime_status,
    diarizer_backend_available,
    diarizer_backend_status,
    packaged_coreml_runners_available,
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
        "xcodebuild_binary": find_xcodebuild_binary(),
        "xcode_select_path": xcode_select_path(),
        "xcode_first_launch_ready": xcode_first_launch_ready(),
        "xcodegen_binary": find_xcodegen_binary(),
        "swift_version": swift_version(),
        "chrome_binary": find_chrome_binary(),
        "chrome_version": chrome_version(),
        "ffmpeg_version": ffmpeg_version(),
        "truststore_enabled": truststore_enabled,
    }

    checks = [
        _check_python(python_version),
        _check_platform(machine),
        _check_xcode_select(env),
        _check_xcode_first_launch(env),
        _check_swift(env),
        _check_xcodegen(env),
        _check_safari_project(),
        _check_safari_build(),
        _check_chrome(env),
        _check_ffmpeg(env),
        _check_ssl(env),
        _check_package("selenium", required=False, message="Selenium is installed for the Chrome fallback flow."),
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
        return _check("chrome", "pass", f"Chrome fallback is available at {chrome_binary}.")
    return _check(
        "chrome",
        "warn",
        "Chrome or Chromium was not found.",
        fix="Safari is now the preferred interactive path. Install Chrome only if you want the legacy Selenium fallback.",
    )


def _check_xcode_select(env: dict[str, object]) -> dict[str, object]:
    if _runtime_release_app_available():
        return _check(
            "xcode-select",
            "pass",
            "Prebuilt release app is present; Xcode command line tools are not required for normal use.",
        )
    path = env["xcode_select_path"]
    if path:
        return _check("xcode-select", "pass", f"Xcode developer directory is set to {path}.")
    return _check(
        "xcode-select",
        "fail",
        "Xcode command line tools are not configured.",
        fix="Install Xcode or Xcode command line tools, then run `xcode-select -p` to verify the active developer directory.",
    )


def _check_xcode_first_launch(env: dict[str, object]) -> dict[str, object]:
    if _runtime_release_app_available():
        return _check(
            "xcode-first-launch",
            "pass",
            "Prebuilt release app is present; Xcode first-launch setup is not required for normal use.",
        )
    ready = env["xcode_first_launch_ready"]
    if ready is True:
        return _check("xcode-first-launch", "pass", "Xcode first-launch setup and license acceptance are complete.")
    if ready is False:
        return _check(
            "xcode-first-launch",
            "fail",
            "Xcode first-launch setup is incomplete.",
            fix="Open Xcode once or run `sudo xcodebuild -license accept` and `sudo xcodebuild -runFirstLaunch`.",
        )
    return _check(
        "xcode-first-launch",
        "warn",
        "Unable to determine Xcode first-launch status.",
        fix="Run `xcodebuild -checkFirstLaunchStatus` locally and complete the required setup if needed.",
    )


def _check_swift(env: dict[str, object]) -> dict[str, object]:
    if packaged_coreml_runners_available():
        return _check("swift", "pass", "Packaged CoreML runners are present; Swift is not required for normal transcription.")
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


def _check_xcodegen(env: dict[str, object]) -> dict[str, object]:
    if _runtime_release_app_available():
        return _check("xcodegen", "pass", "Prebuilt release app is present; xcodegen is not required for normal use.")
    xcodegen_binary = env["xcodegen_binary"]
    if xcodegen_binary:
        return _check("xcodegen", "pass", f"xcodegen available at {xcodegen_binary}.")
    return _check(
        "xcodegen",
        "warn",
        "xcodegen was not found on PATH.",
        fix="Install xcodegen if you want to regenerate the Safari wrapper Xcode project from safari/project.yml.",
    )


def _check_safari_project() -> dict[str, object]:
    if _runtime_release_app_available():
        return _check("safari-project", "pass", "Runtime release does not include the Safari source project; prebuilt app is present.")
    project_spec = safari_project_spec_path()
    project_file = safari_project_path() / "project.pbxproj"
    if project_file.exists():
        return _check("safari-project", "pass", f"Generated Safari Xcode project is present at {project_file}.")
    if project_spec.exists():
        return _check(
            "safari-project",
            "warn",
            f"Safari XcodeGen spec is present at {project_spec}, but the generated project is missing.",
            fix="Run `xcodegen generate --spec safari/project.yml` to regenerate the Safari wrapper project.",
        )
    return _check(
        "safari-project",
        "fail",
        "Safari wrapper project files are missing.",
        fix="Restore `safari/project.yml` and regenerate the Safari wrapper project.",
    )


def _check_safari_build() -> dict[str, object]:
    release_app = _runtime_release_app_path()
    release_extension = release_app / "Contents" / "PlugIns" / "SWinyDLSafariExtension.appex"
    if release_app.exists() and release_extension.exists():
        return _check("safari-app-build", "pass", f"Prebuilt Safari wrapper app is present at {release_app}.")

    app_bundle = safari_built_app_path()
    extension_bundle = safari_extension_bundle_path()
    if app_bundle.exists() and extension_bundle.exists():
        return _check("safari-app-build", "pass", f"Built Safari wrapper app is present at {app_bundle}.")
    if app_bundle.exists():
        return _check(
            "safari-app-build",
            "warn",
            f"Built app exists at {app_bundle}, but the embedded Safari extension bundle is missing.",
            fix="Rebuild the app with `./install.sh` or `xcodebuild` so the extension is embedded in the wrapper app.",
        )
    return _check(
        "safari-app-build",
        "warn",
        f"Built Safari wrapper app was not found at {app_bundle}.",
        fix="Run `./install.sh` to build the wrapper app locally before enabling the Safari extension.",
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


def _runtime_release_app_path() -> Path:
    """Return the prebuilt app location used by GitHub DMG releases."""
    return Path.cwd().resolve() / "SWinyDLSafariApp.app"


def _runtime_release_app_available() -> bool:
    """Return whether this looks like a copied runtime DMG release folder."""
    app = _runtime_release_app_path()
    extension = app / "Contents" / "PlugIns" / "SWinyDLSafariExtension.appex"
    return app.exists() and extension.exists()


def _short_error(message: str) -> str:
    """Collapse long exception text into a short single-line diagnostic."""
    first_line = message.strip().splitlines()[0] if message.strip() else "Unknown error"
    return first_line[:240]
