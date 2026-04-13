# Echo360 Modernization Plan

## Goal

Modernize this project so it runs reliably on current macOS Apple Silicon systems using a current Python runtime, current Selenium/browser automation stack, and a maintained packaging/release path.

This document reflects the state of the repository after the first modernization pass and defines the remaining upgrade sequence.

## Audit Host

- macOS 26.4
- Apple Silicon `arm64`
- machine: Apple M3 Pro
- managed project runtime: Python 3.11+

## Scope

This plan covers:

- runtime modernization
- Apple Silicon compatibility
- packaging and release modernization
- dependency cleanup
- end-to-end validation work

This plan intentionally does **not** include the deferred security hardening pass, except where a change is already required for runtime modernization.

## Current Status

### First Modernization Pass Completed

The following items are already done in the working tree:

- PhantomJS runtime support was removed.
- The default browser path now uses Chrome.
- Selenium 4 locator APIs replaced removed `find_element_by_*` usage.
- Selenium Manager is now used instead of the repo-local driver downloader modules.
- The old `echo360/binary_downloader/` path was removed.
- Python 2 compatibility branches were removed from the active runtime path.
- Bootstrap scripts now target Python 3 and `venv`.
- A minimal `pyproject.toml` was added.
- The CLI/docs were updated to describe the modern browser path.
- Basic parser/default-behavior tests were added.

### Apple Silicon Runtime Status

The source runtime path is now in good shape on Apple Silicon:

- A clean temporary virtual environment install from `requirements.txt` succeeded on this arm64 Mac.
- Installed `gevent` and `greenlet` extension modules contain `arm64` slices.
- Native `ffmpeg` is available on the audit host and the audio/video combine path worked locally.
- Chrome WebDriver startup works locally through Selenium Manager on this Mac.

### Apple Silicon Packaging Status

The standalone binary path is partially proven but not yet repository-ready:

- PyInstaller itself installs on this Mac using a universal2 wheel.
- A local arm64 frozen executable could be produced successfully.
- The committed PyInstaller spec and CI workflow are still stale and do not yet provide an official macOS arm64 artifact path.

## Capability Matrix

| Area | Apple Silicon status | Notes |
| --- | --- | --- |
| Source install in `venv` | Works | Clean temp install completed locally |
| Selenium/browser startup | Works | Chrome driver session launched through Selenium Manager |
| HLS download code path | Likely works | No architecture-specific code remains; still needs live end-to-end Echo360 validation |
| ffmpeg combine/transcode handoff | Works | Local combine smoke test passed with native arm64 ffmpeg |
| Standalone arm64 binary build | Works locally | Built successfully after patching the stale spec in a temp copy |
| Repository macOS arm64 release pipeline | Not set up | No macOS arm64 CI job or artifact publishing yet |

## Remaining Gaps

### 1. No official macOS Apple Silicon release path

The repository can run from source on Apple Silicon, but it does not yet produce or publish a macOS arm64 artifact.

Current blockers:

- `echo360.spec` still hardcodes an old `entrypoint.py` convention and a dead absolute `pathex`.
- `.github/workflows/build.yaml` only builds Linux and Windows artifacts.
- There is no macOS arm64 or universal2 packaging decision encoded in the repo.

### 2. Python support floor was raised

The repository now targets `>=3.11` in packaging, bootstrap, and local environment setup.

Current state:

- package metadata requires `>=3.11`
- the project bootstrap path accepts any compatible Python 3.11+ interpreter
- the local `uv` environment is synced against a compatible Python 3.11+ runtime

Remaining consideration:

- keep local development and CI on a current 3.11+ runtime and avoid reintroducing references to the old macOS system Python

### 3. Dependency simplification is still pending

The processing path is functional, but the dependency stack is still heavier and more fragile than necessary.

Remaining candidates:

- `gevent`
- `pip_ensure_version`
- runtime install behavior for optional packages such as stealth support

This is now a maintainability problem more than an Apple Silicon blocker.

### 4. Live Echo360 validation is still required

We have local smoke validation for browser startup and processing helpers, but not yet full live-flow validation against current Echo360 deployments.

Still needed:

- standard `/ess/portal/section/...` flow
- Echo360 Cloud flow
- interactive login path
- persistent session path
- alternative feeds path

### 5. Docs are only partially refreshed

The docs no longer describe PhantomJS or manual driver setup, but they still need a true “supported setup” section for modern macOS Apple Silicon.

## Upgrade Sequence

### Phase 1: Runtime Modernization

Status: completed

Scope:

- remove PhantomJS
- move to Selenium 4 APIs
- replace local driver downloads with Selenium Manager
- switch bootstrap/runtime to Python 3-only behavior

Acceptance:

- CLI help matches the supported options
- Chrome driver startup works on Apple Silicon without manual driver management
- UUID-only CLI input no longer crashes before runtime

### Phase 2: Apple Silicon Packaging And Release Path

Status: pending

Why this is next:

- Source execution already works on Apple Silicon.
- The main missing capability is an official build/release story.

Required changes:

1. Rewrite `echo360.spec` to use repository-relative inputs instead of stale hardcoded paths.
2. Decide whether to ship:
   - `arm64` only, or
   - `universal2`
3. Add a macOS build job to `.github/workflows/build.yaml`.
4. Publish a macOS artifact alongside Linux and Windows artifacts.
5. Verify the frozen binary starts successfully on Apple Silicon.

Acceptance:

- CI produces a macOS binary artifact.
- The produced binary reports the expected architecture.
- The binary starts and shows `--help` on an Apple Silicon host.

### Phase 3: Dependency And Processing Simplification

Status: pending

Why this follows Phase 2:

- Runtime compatibility is already established.
- Now the remaining work is mostly about reducing fragility and maintenance cost.

Required changes:

1. Decide whether `gevent` remains justified for HLS download concurrency.
2. If not, replace it with:
   - `concurrent.futures`, or
   - an `asyncio` implementation
3. Remove runtime self-install behavior where practical.
4. Tighten dependency constraints around the working modern stack.
5. Re-test the HLS join and transcode paths after any concurrency refactor.

Acceptance:

- Clean install continues to work on Apple Silicon.
- The HLS processing path still works.
- There are fewer compiled or runtime-installed dependencies.

### Phase 4: End-To-End Echo360 Validation

Status: pending

Required changes:

1. Validate a standard Echo360 course flow with current Chrome.
2. Validate Echo360 Cloud login and content discovery.
3. Validate persistent session behavior on macOS.
4. Validate headless and interactive behavior where both are expected to work.
5. Record known-good test notes in the repo.

Acceptance:

- A real lecture/course can be discovered and downloaded on Apple Silicon.
- Session reuse behavior is predictable.
- Known working paths are documented.

### Phase 5: Documentation Refresh

Status: pending

Required changes:

1. Add a current macOS Apple Silicon install section.
2. Document required Python version.
3. Document browser expectations.
4. Document `ffmpeg` as optional but recommended.
5. Document whether release artifacts are `arm64` or `universal2`.

Acceptance:

- A new Apple Silicon user can follow the README without repo knowledge.
- Docs match the real supported path.

### Phase 6: Deferred Security Hardening

Status: intentionally deferred

This remains a separate pass and should not be mixed into the packaging/validation work unless a specific runtime issue forces it.

Deferred topics include:

- credential handling cleanup
- log redaction
- runtime package installation removal
- dependency advisory cleanup
- session/profile storage review

## Recommended Next Implementation Pass

The next pass should focus on official Apple Silicon release support, not another runtime refactor.

Recommended concrete tasks:

1. Replace the stale `echo360.spec` with a current repo-relative spec.
2. Add a macOS arm64 CI job.
3. Decide between `arm64` and `universal2` artifacts.
4. Build and publish a macOS artifact in CI.
5. Add one binary smoke check in CI.

## Local Validation Notes

Observed locally on the audit host:

- clean temporary `venv` install from `requirements.txt` succeeded
- Chrome WebDriver session launched through Selenium Manager
- native arm64 `ffmpeg` was present and worked with the combine path
- PyInstaller produced a native arm64 executable locally

Not yet completed:

- full live download from an actual Echo360 course on Apple Silicon
- official CI-produced macOS artifact
- final Python floor uplift to `>=3.11`
