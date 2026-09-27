# SWinyDL Technical Overview

SWinyDL downloads and transcribes Echo360 lecture recordings on Apple Silicon Macs. This page covers how it works, the command line, the speech models, building from source and releases.

For installing and using the app, see the root [README](../README.md) and the [user guide](user-guide.md).

## Parts

- **Safari extension** (`safari/SWinyDLSafariExtension/`). Runs on Canvas (`*.instructure.com`) and Echo360 pages (`echo360.net.au`, `*.echo360.net.au`, `*.echo360.org`, `*.echo360.net`, `*.streaming.sydney.edu.au`). It finds the lessons on the page and lets you pick them.
- **Mac app** (`safari/SWinyDLSafariApp/`). `SWinyDLSafariApp.app` contains the extension. It keeps the job queue, the output folder setting and the readiness checks, and it starts the Python backend for each job.
- **Python backend** (`swinydl/`). The `swinydl` command line tool. It finds lessons, downloads media with yt-dlp, and writes the transcripts.
- **CoreML runners** (`swift/ParakeetCoreMLRunner/`). Two Swift programs, `parakeet-coreml-runner` and `speaker-diarizer-coreml-runner`. The release DMG ships them prebuilt in `bin/`. A source checkout builds them with `swift build` when they are first needed.

## How a Safari Job Runs

1. You pick lessons in the extension popup.
2. The extension exports only the cookies Safari would send to the course page and the source page (`browser.cookies.getAll({url})` for each URL).
3. It writes a job manifest with those cookies into the app-group container and opens the app.
4. The app runs `swinydl process-manifest` on the manifest. Jobs wait until an output folder is chosen.
5. The backend writes progress to a status file next to the manifest. The app shows it.

Job manifests, logs, temporary files and debug exports live in the app-group container, in the `Jobs`, `Logs`, `Temp` and `DebugExports` folders. Transcripts go only to the output folder chosen in the app.

## Transcription Pipeline

1. The lesson's media is downloaded and converted to mono 16 kHz WAV with `ffmpeg`.
2. `parakeet-coreml-runner` transcribes it with the Parakeet CoreML model and returns token timings as JSON.
3. `speaker-diarizer-coreml-runner` separates speakers, unless diarization is off.
4. Python rebuilds words and segments and writes `.txt`, `.srt` and `.json`. The `.txt` file is the main transcript.

Speaker separation is on by default. With `--diarization off`, `process` uses a lesson's existing Echo360 captions when it has them (`--transcript-source auto`), and falls back to speech recognition when it does not. The caption parser reads SRT and WebVTT. It accepts WebVTT timestamps with or without hours and cues that are not separated by blank lines.

## Command Line

Run commands with `uv run` from the copied `SWinyDL` folder or a source checkout, after `./install.sh`. `uv run swinydl <command> --help` shows every option.

| Command | What it does |
| --- | --- |
| `inspect COURSE_URL` | Lists a course's lessons and assets. `--json` prints JSON. |
| `process COURSE_URL` | Downloads and transcribes lessons. |
| `download COURSE_URL` | Downloads media only. `--media audio` (default), `video` or `both`. |
| `process-manifest PATH` | Runs a job manifest written by the Safari extension. The manifest carries its own cookies. |
| `transcribe PATH` | Transcribes a local media file. A `.srt` or `.vtt` file is converted without speech recognition. |
| `bootstrap-models` | Downloads the CoreML models. `--target all` (default), `parakeet` or `diarizer`. `--force` downloads again. |
| `doctor` | Checks the runtime. `--json` prints JSON. |

### Cookies

`inspect`, `process` and `download` need exactly one cookie source:

- `--cookies-from-browser {safari,chrome,chromium,firefox,edge,brave}` reads that browser's cookie store through yt-dlp. Log in to the course in that browser first. Reading Safari's cookies needs Full Disk Access for your terminal app. Chrome asks for Keychain access.
- `--cookies FILE` reads a Netscape-format `cookies.txt` file.

Only cookies for the course URL's host and its parent domains are used. If none match, the command stops and says so.

`process-manifest` and `transcribe` take no cookie options.

### Lesson selection

`inspect`, `process` and `download` accept:

- `--lesson-id ID` (repeatable)
- `--title-match TEXT`
- `--after-date DATE` and `--before-date DATE`
- `--latest N`
- `--limit N`

### Output and processing options

- `--output`, `-o` sets the output folder. The default is `swinydl-output/` in the current folder.
- `--asr-backend auto` resolves to the local Parakeet CoreML runner. `parakeet` is the only other choice.
- `--diarization {auto,on,off}` controls speaker separation. The default is `on`.
- `--transcript-source {auto,native,asr}` (`process` only) chooses between existing captions and speech recognition when diarization is off.
- `--keep-audio` (`process`, `transcribe`) keeps the converted `.wav` file in the output folder.
- `--force` (`process`) transcribes a lesson again even when its `.json` already exists.

Examples:

```bash
uv run swinydl inspect COURSE_URL --cookies-from-browser safari --json
uv run swinydl process COURSE_URL --cookies-from-browser safari --latest 3
uv run swinydl download COURSE_URL --cookies cookies.txt --media both
uv run swinydl transcribe ~/Downloads/lecture.mp4 --output ~/Documents/transcripts
```

When run from the command line, temporary files go to `temp/` in the current folder. `SWINYDL_TEMP_ROOT` overrides this.

### Doctor

`swinydl doctor` checks Python (3.11 or newer), macOS on Apple Silicon, `ffmpeg`, the macOS trust store for HTTPS, yt-dlp, and both CoreML models. It also checks the Xcode tools, Swift, `xcodegen` and the Safari project. Those developer checks pass automatically in a DMG folder, where the prebuilt app and runners are present.

## Speech Models

`swinydl bootstrap-models` downloads the models from Hugging Face into the `vendor/` folder of the SWinyDL folder or source checkout:

- `vendor/parakeet-tdt-0.6b-v3-coreml`
- `vendor/speaker-diarization-coreml`

The backend reads the models from `vendor/` next to the `swinydl` package. Run the command from the SWinyDL folder or checkout. `./install.sh` runs it for you. Existing models are skipped unless you pass `--force`.

To use models stored elsewhere, set `ECHO360_PARAKEET_COREML_DIR` and `ECHO360_DIARIZER_COREML_DIR`.

### Model sources

- ASR CoreML download: [FluidInference/parakeet-tdt-0.6b-v3-coreml](https://huggingface.co/FluidInference/parakeet-tdt-0.6b-v3-coreml)
- ASR base model: [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- Diarizer CoreML download: [FluidInference/speaker-diarization-coreml](https://huggingface.co/FluidInference/speaker-diarization-coreml)
- Diarizer base pipeline: [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

The diarizer corresponds to:

- segmentation from [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
- speaker embeddings from [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM)
- VBx-style clustering parameters from the `community-1` pipeline

When updating models, use the CoreML repositories for the files and the base model cards to check architecture or license changes. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for licenses.

## Building From Source

The DMG is the normal install. Build from source only to change or inspect the app, backend or packaging.

You need:

- an Apple Silicon Mac with Safari
- Apple's command line tools (`xcode-select --install`), with Xcode first-launch setup complete
- Homebrew, `uv`, `ffmpeg` and `xcodegen`. `./install.sh --build-from-source` offers to install any that are missing.

```bash
git clone https://github.com/david00769/swinydl.git
cd swinydl
./scripts/build_app.sh
./install.sh
```

Or in one step:

```bash
./install.sh --build-from-source
```

`scripts/build_app.sh` regenerates `safari/SWinyDLSafari.xcodeproj` from `safari/project.yml` with `xcodegen`, builds `SWinyDLSafariApp.app` with `xcodebuild`, copies the WebExtension files into the extension, ad-hoc signs the app and verifies it, and places it at `SWinyDLSafariApp.app` in the repository root. Run `./scripts/build_app.sh --help` for its options.

`./install.sh` without `--build-from-source` does not compile anything. It needs a prebuilt `SWinyDLSafariApp.app` in the folder.

To check that macOS has registered the extension:

```bash
pluginkit -mAvvv -p com.apple.Safari.web-extension | grep com.davidsiroky.swinydl
```

Run the tests with:

```bash
uv run pytest
```

Dependency ranges are in `pyproject.toml`. The tested resolution is in `uv.lock`.

## Releases

GitHub Releases are the update source. The app's update check reads the latest release from GitHub.

Pushing a tag that starts with `v` runs `.github/workflows/release-dmg.yaml`. It installs `xcodegen`, runs `scripts/package_release.sh`, and attaches the unsigned `SWinyDL-vX.Y.Z.dmg` to the GitHub release. The workflow can also be run by hand with a version. Every run also uploads the DMG as a workflow artifact.

`scripts/package_release.sh` builds a Release app and the two CoreML runners, then stages a runtime-only folder. The DMG contains:

- `SWinyDLSafariApp.app`
- `install.sh`, `pyproject.toml` and `uv.lock`
- the `swinydl` Python package
- `bin/parakeet-coreml-runner` and `bin/speaker-diarizer-coreml-runner`
- `vendor/`, where setup puts the models
- `WebExtension/` and `SWinyDL-WebExtension.zip`, for Safari's temporary-extension fallback
- `README.md` (from [release-install.md](release-install.md)) and `USER-GUIDE.md` (from [user-guide.md](user-guide.md))
- `LICENSE` and `THIRD_PARTY_NOTICES.md`

It does not contain the Xcode project, Swift sources, build scripts or tests.

The app is unsigned. Signing and notarization would remove the need for the Control-click open, the `Allow unsigned extensions` setting and the Terminal repair steps.
