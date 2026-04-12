# SWinyDL v4

SWinyDL: transcript-first Echo360 tooling for macOS Apple Silicon.

This repository is designed specifically for Apple Silicon Macs. It is not intended as a general cross-platform package.

Tested platform:
- macOS 26.4 (`25E246`) on Apple Silicon

`swinydl` keeps the Echo360-specific discovery and media retrieval flow, but replaces the old custom HLS downloader with `yt-dlp`, makes transcription the default product path, and now treats Safari as the preferred interactive entrypoint.

For day-to-day use, the primary path is:

```bash
./install.sh
```

That installer:

- validates local prerequisites
- runs `uv sync`
- bootstraps the staged CoreML bundles
- regenerates and builds the Safari wrapper app
- opens the app and Safari so you can enable the extension

Then:

1. Enable `SWinyDL Safari` in Safari Settings
2. Open a logged-in Canvas or Echo360 page in Safari
3. Use the extension popup to select lessons and choose whether downloaded media should be deleted after transcription
4. Watch stage-by-stage progress in the native wrapper window, including active lesson, elapsed time, recent activity, and the emitted `.txt`, `.srt`, and `.json` files

## First-Time Mac User

If you are not technical, use this path and ignore the rest of the commands in this README:

1. Install Apple’s command line tools by running `xcode-select --install`
2. Install Homebrew if you do not already have it
3. Install the three tools SWinyDL expects:

```bash
brew install uv ffmpeg xcodegen
```

4. In Terminal, change into the SWinyDL folder
5. Run:

```bash
./install.sh
```

6. Wait for the installer to finish
7. In Safari, open `Settings > Extensions` and enable `SWinyDL Safari`
8. If the extension does not appear, open Safari’s Develop menu and turn on `Allow Unsigned Extensions`
9. Open your Canvas or Echo360 page in Safari and use the extension popup

What `./install.sh` does for you:

- creates the Python environment
- downloads the Parakeet and speaker-diarizer model files if they are missing
- builds the Mac app and Safari extension
- opens the app and Safari when setup is finished

You do not need to download the Parakeet model manually.

The Chrome-guided launcher still exists as a fallback:

```bash
uv run app.py
```

## What v4 Does

- inspects Echo360 courses and lists lessons
- adds a Safari Web Extension popup for whole-course lesson selection
- adds a native macOS wrapper app that launches backend jobs and shows progress
- prefers speaker-aware ASR by default so transcripts include speaker labels
- can reuse native Echo360 captions when you explicitly turn diarization off
- runs a local `Parakeet` CoreML backend on Apple Silicon
- keeps diarization as a separate local CoreML speaker pipeline
- writes `.txt`, `.srt`, and structured `.json` outputs, with `.txt` treated as the primary user-facing transcript
- deletes temporary media after successful transcription unless you opt in to keep it
- supports explicit media download as a separate subcommand
- is tuned for lecture-style content with one dominant speaker and occasional audience participation

## Scope

- macOS Apple Silicon only
- tested on macOS `26.4` (`25E246`)
- Safari-first interactive flow, Chrome fallback only
- local developer-style install from the repo, not App Store distribution
- Python `>=3.11`
- package distribution via `pip` or `uv`
- Swift toolchain via Xcode command line tools
- `xcodegen` for regenerating the Safari Xcode project
- no Windows support
- no Firefox support
- no PhantomJS support

## Install

### Recommended: local repo install with Safari

```bash
./install.sh
```

This is the supported install flow for this repo.

It checks:

- Python `>=3.11`
- `uv`
- `ffmpeg`
- `xcodegen`
- `xcode-select`
- Xcode first-launch and license acceptance

It builds the containing app at:

```text
./safari/.build/Debug/SWinyDLSafariApp.app
```

After the installer finishes:

1. In Safari, open `Settings > Extensions`
2. Enable `SWinyDL Safari`
3. If the extension does not appear, enable Safari's Develop menu and turn on `Allow Unsigned Extensions`
4. If you want to confirm Safari sees the extension bundle, run:

```bash
pluginkit -mAvvv -p com.apple.Safari.web-extension | rg SWinyDL
```

5. Open a logged-in Canvas or Echo360 page and use the extension popup to launch jobs

How to tell if the models are ready:

- the Mac app header shows `Models ready` when both model bundles are present
- the empty state also shows `Parakeet ASR: Ready` and `Speaker diarizer: Ready`
- from Terminal, `swinydl doctor` should complete with no failures

The Safari popup includes a default-on setting:

- `Delete downloaded media after transcription to conserve disk space`

When that setting stays on, SWinyDL removes downloaded media after transcript generation. If you turn it off, `Download + Transcribe` retains the downloaded media files on disk.

The native wrapper app shows the transcript artifacts for successful lessons and exposes `Open Transcription Folder` so you can jump straight to the generated files.

### Manual install if you do not want the guided script

```bash
uv sync
swinydl bootstrap-models
xcodegen generate --spec safari/project.yml
xcodebuild \
  -project safari/SWinyDLSafari.xcodeproj \
  -scheme SWinyDLSafariApp \
  -configuration Debug \
  -derivedDataPath safari/.build/DerivedData \
  CONFIGURATION_BUILD_DIR="$PWD/safari/.build/Debug" \
  CODE_SIGNING_ALLOWED=NO \
  build
open safari/.build/Debug/SWinyDLSafariApp.app
open -a Safari
```

### Python-only fallback install

```bash
uv sync
```

or:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Dependency Management

- [pyproject.toml](pyproject.toml) defines the allowed dependency ranges for the package.
- [uv.lock](uv.lock) records the currently tested resolution.
- `swinydl doctor` checks runtime readiness only. It does not manage package versions.
- There is no separate `requirements.txt` or `MANIFEST.in` to maintain in v4. Packaging and dependency policy live in `pyproject.toml`.
- Third-party model and dependency provenance is documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Upgrade to newer compatible dependency versions with:

```bash
uv lock --upgrade
uv sync
```

## Requirements

- Safari enabled with the SWinyDL extension for the preferred interactive flow
- Xcode or Xcode command line tools installed and selected via `xcode-select`
- Xcode first-launch setup and license acceptance complete
- Swift installed via Xcode command line tools
- `xcodegen` on `PATH`
- `ffmpeg` on `PATH`
- local Parakeet CoreML assets staged at `./vendor/parakeet-tdt-0.6b-v3-coreml` or exposed through `ECHO360_PARAKEET_COREML_DIR`
- local speaker diarizer CoreML assets staged at `./vendor/speaker-diarization-coreml` or exposed through `ECHO360_DIARIZER_COREML_DIR`
- Chrome or Chromium only if you want the legacy Selenium fallback

## Quickstart

For a new machine, the shortest supported path is:

1. `./install.sh`
2. Enable the SWinyDL Safari extension in Safari Settings
3. Open a supported Canvas or Echo360 page in Safari and use the extension popup to launch jobs
4. Or use direct CLI fallback:

```bash
swinydl process COURSE_URL
swinydl process-manifest /path/to/job.json
swinydl transcribe /path/to/local/file.mp4
```

`uv sync` installs the Python dependencies declared in [pyproject.toml](pyproject.toml), including the Hugging Face client used by model bootstrap. The first time the CoreML runners are built, Swift Package Manager also resolves the Swift-side dependency declared in [Package.swift](swift/ParakeetCoreMLRunner/Package.swift).

If the staged model bundles are missing, `swinydl process`, `swinydl process-manifest`, `swinydl transcribe`, `swinydl doctor`, and `uv run app.py` will auto-bootstrap the default repo-local model bundles automatically.

## Updating SWinyDL

GitHub Releases are the source of truth for updates:

- [david00769/swinydl releases](https://github.com/david00769/swinydl/releases)

The native Safari wrapper checks GitHub Releases on launch and from `Check for Updates...`. Under the current unsigned local-install model, updates are guided rebuilds, not in-place binary patching.

When a new release is available, update with:

```bash
git pull --tags
uv sync
./install.sh
```

Run `swinydl bootstrap-models` separately only if the release notes mention model layout changes.

If the wrapper app cannot resolve the local repo root, it falls back to opening the GitHub release page and the local README update instructions.

If you have not published any GitHub Releases yet, the native wrapper's update check will report that no releases were found. That is expected. The release-check UI only becomes meaningful after the first published GitHub release tag.

## Troubleshooting

### Safari extension does not appear

1. Make sure the containing app exists at:

```text
./safari/.build/Debug/SWinyDLSafariApp.app
```

2. Run the app once:

```bash
open ./safari/.build/Debug/SWinyDLSafariApp.app
```

3. Open Safari and check `Settings > Extensions`
4. If the extension is still missing, enable Safari's Develop menu and turn on `Allow Unsigned Extensions`
5. Confirm Safari has registered the extension:

```bash
pluginkit -mAvvv -p com.apple.Safari.web-extension | rg SWinyDL
```

6. If the built app or embedded extension is missing, rebuild with:

```bash
./install.sh
```

You can also confirm the app health directly with:

```bash
swinydl doctor
```

### Where do the transcript files show up?

The native wrapper app now shows the emitted transcript files for each successful lesson. `.txt` is the primary transcript most users care about, while `.srt` and `.json` remain available as secondary artifacts:

- `.txt` for the main readable transcript
- `.srt` for timed captions
- `.json` for structured transcript and status data

Each lesson row exposes:

- `Preview TXT` for an in-app text preview
- `Open Transcript` with `.txt` preferred by default
- `Open Transcription Folder` for the full artifact directory

### Backend runs feel slow or silent

The native wrapper now shows stage-level status for `downloading`, `extracting audio`, `transcribing`, `diarizing`, and `writing files`, plus active lesson, elapsed time, and a recent activity log.

The CoreML runners still do not expose fine-grained token-level inference progress, so some stages can remain visually steady for a while on large lectures.

What has been verified locally:

- unattended `swinydl transcribe` works on public sample media
- diarized and non-diarized local transcription both complete successfully
- concurrent transcribes no longer collide on shared temp paths or model bootstrap state

If a run appears stuck for an unusually long time, check the output directory and rerun:

```bash
swinydl doctor
```

### Update check says no releases were found

That means the GitHub repo does not have a published release yet. The app checks:

- [david00769/swinydl releases](https://github.com/david00769/swinydl/releases)

Publish a first release there if you want the wrapper app to notify about new versions.

## Bootstrap Models

The repo ignores downloaded model bundles under `vendor/` because they can be recreated from public Hugging Face sources.

Those staged bundles are third-party assets and are not covered by this repository's MIT license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

`bootstrap-models` downloads every staged model artifact the runtime expects:

- Parakeet ASR CoreML bundles:
  - `Preprocessor.mlmodelc/**`
  - `Encoder.mlmodelc/**`
  - `Decoder.mlmodelc/**`
  - `JointDecision.mlmodelc/**`
  - `parakeet_vocab.json`
- Speaker diarizer CoreML bundles:
  - `Segmentation.mlmodelc/**`
  - `FBank.mlmodelc/**`
  - `Embedding.mlmodelc/**`
  - `PldaRho.mlmodelc/**`
  - `plda-parameters.json`
  - `xvector-transform.json`

Use the built-in bootstrap command:

```bash
swinydl bootstrap-models
```

Fetch only one bundle if needed:

```bash
swinydl bootstrap-models --target parakeet
swinydl bootstrap-models --target diarizer
```

Re-download staged files:

```bash
swinydl bootstrap-models --force
```

### Stage a Local Parakeet CoreML Bundle

`swinydl` expects a staged CoreML model directory with this layout:

```text
vendor/parakeet-tdt-0.6b-v3-coreml/
  Preprocessor.mlmodelc/
  Encoder.mlmodelc/
  Decoder.mlmodelc/
  JointDecision.mlmodelc/
  parakeet_vocab.json
```

The runtime uses that directory offline through the Swift/CoreML runner. Pull the staged bundle directly from the upstream CoreML repo with:

```bash
swinydl bootstrap-models --target parakeet
```

### Model Provenance And Update Sources

The repo consumes staged local CoreML bundles, but those bundles come from public upstream model repos.

For ASR, the current update chain is:

- preferred public CoreML pull source: [FluidInference/parakeet-tdt-0.6b-v3-coreml](https://huggingface.co/FluidInference/parakeet-tdt-0.6b-v3-coreml)
- canonical base model: [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)

The local staged directory names map to the CoreML conversion artifacts:

- `Preprocessor.mlmodelc`
- `Encoder.mlmodelc`
- `Decoder.mlmodelc`
- `JointDecision.mlmodelc`
- `parakeet_vocab.json`

For speaker diarization, the current update chain is:

- preferred public CoreML pull source: [FluidInference/speaker-diarization-coreml](https://huggingface.co/FluidInference/speaker-diarization-coreml)
- canonical base pipeline: [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

The local diarizer bundle is a CoreML packaging of the same conceptual pipeline pieces used by the pyannote `community-1` stack:

- segmentation: [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
- speaker embedding: [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM)
- clustering family: VBx, documented in the `community-1` model card citations

When updating this repo, prefer the public CoreML repos first. Use the canonical upstream Hugging Face model cards to understand architecture changes, licenses, and benchmark shifts. Treat local `vendor/` contents as staged runtime artifacts, not as the authoritative source of model lineage.

## Commands

### Safari-first interactive flow

`./install.sh` is the primary supported setup path. It leaves you with a built Safari app in `./safari/.build/Debug/SWinyDLSafariApp.app`.

The Safari app + extension path is the preferred interactive flow. The extension loads the full course inventory from the current logged-in Safari page, then sends a manifest-driven job into the native wrapper app.

### Inspect a course

```bash
swinydl inspect "https://echo360.org.au/section/UUID/home"
```

### Default transcript workflow

```bash
swinydl process "https://echo360.org.au/section/UUID/home"
```

`process` is the normal product path: inspect lessons, fetch the best audio path, transcribe it, and label speaker turns by default.

The Safari wrapper launches the backend through the manifest entrypoint:

```bash
swinydl process-manifest /path/to/job.json
```

The equivalent legacy browser-guided fallback is:

```bash
uv run app.py
```

That launcher remains Chrome-based and:

1. asks you to press Enter to launch Chrome
2. opens Chrome with the app's persistent profile
3. lets you log in and navigate to the right Canvas or Echo360 page
4. captures the current browser URL when you press Enter again
5. runs the default `process` workflow against that captured page

### Force the local Parakeet CoreML backend

```bash
swinydl process "https://echo360.org.au/section/UUID/home" --asr-backend parakeet
```

### Keep normalized audio

```bash
swinydl process "https://echo360.org.au/section/UUID/home" --keep-audio
```

### Download media explicitly

```bash
swinydl download "https://echo360.org.au/section/UUID/home" --media both
```

Use `download` when you explicitly want Echo360 media artifacts on disk. Use `process` for the normal inspect -> fetch audio -> transcribe flow.

### Transcribe a local file

```bash
swinydl transcribe ~/Downloads/lecture.mp4
```

### Control speaker separation explicitly

```bash
swinydl transcribe ~/Downloads/lecture.mp4 --diarization on
```

Disable speaker separation only when you want raw caption reuse or the fastest possible transcript path:

```bash
swinydl transcribe ~/Downloads/lecture.mp4 --diarization off
```

### Environment check

```bash
swinydl doctor
```

`doctor` is a runtime health check. It validates the local environment for Xcode command line readiness, Swift, xcodegen, the generated Safari project, the built Safari wrapper app, Chrome fallback availability, ffmpeg, the local Parakeet CoreML backend, and the local CoreML speaker diarizer. It does not install dependencies or decide package versions.

JSON output is also available:

```bash
swinydl doctor --json
```

## Verification Status

What has been verified locally:

- the CLI boots and the test suite passes
- the local Parakeet CoreML transcription path runs end to end
- the local CoreML diarization path runs end to end
- unattended transcription succeeds on public sample media without human input
- concurrent transcribes of the same sample now complete successfully
- transcript artifacts are emitted as `.txt`, `.srt`, and `.json`, with `.txt` emphasized in the native app

What is still being tuned:

- diarization quality for short back-and-forth dialogue is not good enough yet
- the current pipeline can collapse two-speaker conversations into one dominant label
- the intended target remains lecture-style audio with one primary speaker and occasional questions or interruptions
- the live Safari-authenticated Canvas/Echo360 path still needs more real-world validation after the recent backend concurrency fixes

So the current state is:

- transcription: working
- speaker separation execution: working
- speaker separation quality: still under active tuning

## Defaults

- default command: `process`
- default output root: `./swinydl-output`
- default transcript source: `auto`
- default ASR backend: `auto`
- default diarization mode: `on`
- default outputs: `.txt`, `.srt`, `.json`
- default primary deliverable: `.txt`
- default media policy: delete temporary media after success
- default interactive entrypoint: Safari wrapper app + Safari Web Extension
- default browser/session fallback: persistent Chrome profile in `~/Library/Application Support/swinydl/browser-profile/`

Output layout:

```text
./swinydl-output/<course-slug>/<lesson-key>.txt
./swinydl-output/<course-slug>/<lesson-key>.srt
./swinydl-output/<course-slug>/<lesson-key>.json
./swinydl-output/<course-slug>/_runs/<run-id>.json
```

`lesson-key` format:

```text
<date-or-undated>__<lesson-id-or-index>__<slug>
```

## Migration From The Old CLI

- the old interactive picker is gone
- the old custom downloader stack is gone
- Firefox, PhantomJS, and bundled driver downloaders are gone
- video download is now explicit via `swinydl download`
- the legacy `swinydl-downloader` alias is no longer part of the main supported surface; use `swinydl process` or `swinydl download`
- the CLI now targets a local Parakeet CoreML backend
- packaging is driven by `pyproject.toml` and `uv.lock`; there is no separate `requirements.txt` workflow

## Backend Notes

- `--asr-backend auto` resolves to the local Parakeet CoreML backend.
- The default model directory is `./vendor/parakeet-tdt-0.6b-v3-coreml`.
- Set `ECHO360_PARAKEET_COREML_DIR` to point at a different staged CoreML repo directory.
- Set `ECHO360_PARAKEET_COREML_VERSION=v2` if you stage the English-only v2 CoreML bundle instead.
- The Python CLI does not run Parakeet directly. It shells into a small Swift helper that loads the CoreML bundles, runs transcription on Apple Silicon, and returns token timings as JSON.
- Token timings are reconstructed into words and transcript segments in Python, then written to `.txt`, `.srt`, and `.json`.
- Speaker diarization is also local. Python shells into a second Swift helper that loads the staged CoreML diarizer bundles and returns speaker segments as JSON.
- The default diarizer model directory is `./vendor/speaker-diarization-coreml`.
- Set `ECHO360_DIARIZER_COREML_DIR` to point at a different staged diarizer model directory.
- The current diarization defaults are chosen for lecture-style media, not highly conversational two-speaker content.
- The repo-local `vendor` model directory is ignored by git because the staged CoreML bundle is large and machine-local.

### Stage a Local Speaker Diarizer CoreML Bundle

`swinydl` expects a staged diarizer directory with this layout:

```text
vendor/speaker-diarization-coreml/
  Segmentation.mlmodelc/
  FBank.mlmodelc/
  Embedding.mlmodelc/
  PldaRho.mlmodelc/
  plda-parameters.json
  xvector-transform.json
```

The diarization runner loads those offline CoreML assets directly through Swift/CoreML. Pull the staged bundle directly from the upstream CoreML repo with:

```bash
swinydl bootstrap-models --target diarizer
```

The repo currently expects these local filenames, even though upstream bundles may use different names internally:

- `Segmentation.mlmodelc`
- `FBank.mlmodelc`
- `Embedding.mlmodelc`
- `PldaRho.mlmodelc`
- `plda-parameters.json`
- `xvector-transform.json`

If an upstream CoreML release changes file names but not the underlying model roles, keep the repo-local staged names stable and adapt the staging step.

## Development

Create a local environment and install the package in editable mode:

```bash
uv sync --group dev
./.venv/bin/python -m unittest discover -s tests -v
```
