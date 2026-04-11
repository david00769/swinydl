# SWinyDL v4

SWinyDL: transcript-first Echo360 tooling for macOS Apple Silicon.

This repository is designed specifically for Apple Silicon Macs. It is not intended as a general cross-platform package.

Tested platform:
- macOS 26.4 (`25E246`) on Apple Silicon

`swinydl` keeps the Echo360-specific browser login and lesson discovery flow, but replaces the old custom HLS downloader with `yt-dlp` and makes transcription the default product path.

For day-to-day use, the simplest launch path is:

```bash
uv run app.py
```

If you launch it with no arguments, the app:

1. asks you to press enter to launch Chrome
2. lets you log in and navigate to the target page
3. captures the browser URL when you press enter again
4. runs the default `process` workflow against that captured URL

On first real use, if the default local CoreML model bundles are missing, the app automatically downloads them from the documented Hugging Face sources before continuing.

## What v4 Does

- inspects Echo360 courses and lists lessons
- prefers speaker-aware ASR by default so transcripts include speaker labels
- can reuse native Echo360 captions when you explicitly turn diarization off
- runs a local `Parakeet` CoreML backend on Apple Silicon
- keeps diarization as a separate local CoreML speaker pipeline
- writes `.txt`, `.srt`, and structured `.json` outputs
- deletes temporary media after successful transcription unless you opt in to keep it
- supports explicit media download as a separate subcommand
- is tuned for lecture-style content with one dominant speaker and occasional audience participation

## Scope

- macOS Apple Silicon only
- tested on macOS `26.4` (`25E246`)
- Chrome or Chromium only
- Python `>=3.11`
- package distribution via `pip` or `uv`
- Swift toolchain via Xcode command line tools
- no Windows support
- no Firefox support
- no PhantomJS support

## Install

### `uv`

```bash
uv sync
```

### `pip`

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

- Google Chrome or Chromium installed
- Swift installed via Xcode command line tools
- `ffmpeg` on `PATH`
- an interactive Echo360 login in the Chrome profile on first use
- local Parakeet CoreML assets staged at `./vendor/parakeet-tdt-0.6b-v3-coreml` or exposed through `ECHO360_PARAKEET_COREML_DIR`
- local speaker diarizer CoreML assets staged at `./vendor/speaker-diarization-coreml` or exposed through `ECHO360_DIARIZER_COREML_DIR`

## Quickstart

For a new machine, the shortest supported path is:

1. `uv sync`
2. `swinydl bootstrap-models`
3. Run `swinydl doctor`
4. Run `uv run app.py`, press enter to launch Chrome, then log in and navigate to the target page before pressing enter again
5. Or bypass the browser-guided flow and run `swinydl transcribe /path/to/local/file.mp4` for a local file

`uv sync` installs the Python dependencies declared in [pyproject.toml](pyproject.toml), including the Hugging Face client used by model bootstrap. The first time the CoreML runners are built, Swift Package Manager also resolves the Swift-side dependency declared in [Package.swift](swift/ParakeetCoreMLRunner/Package.swift).

If you skip step 2, `swinydl process`, `swinydl transcribe`, `swinydl doctor`, and `uv run app.py` will auto-bootstrap the default repo-local model bundles when they are missing.

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

### Inspect a course

```bash
swinydl inspect "https://echo360.org.au/section/UUID/home"
```

### Default transcript workflow

```bash
swinydl process "https://echo360.org.au/section/UUID/home"
```

`process` is the normal product path: inspect lessons, fetch the best audio path, transcribe it, and label speaker turns by default.

The equivalent friendly launcher is:

```bash
uv run app.py
```

That launcher:

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

`doctor` is a runtime health check. It validates the local environment for Swift, Chrome, ffmpeg, the local Parakeet CoreML backend, and the local CoreML speaker diarizer. It does not install dependencies or decide package versions.

JSON output is also available:

```bash
swinydl doctor --json
```

## Verification Status

What has been verified locally:

- the CLI boots and the test suite passes
- the local Parakeet CoreML transcription path runs end to end
- the local CoreML diarization path runs end to end
- transcript artifacts are emitted as `.txt`, `.srt`, and `.json`

What is still being tuned:

- diarization quality for short back-and-forth dialogue is not good enough yet
- the current pipeline can collapse two-speaker conversations into one dominant label
- the intended target remains lecture-style audio with one primary speaker and occasional questions or interruptions

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
- default media policy: delete temporary media after success
- default browser/session policy: persistent Chrome profile in `~/Library/Application Support/swinydl/browser-profile/`

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
