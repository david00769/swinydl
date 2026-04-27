# SWinyDL v4

See the repository root [README](../README.md) for the supported install and usage flow.

The v4 line is transcript-first:

- Safari wrapper app + Safari Web Extension
- `swinydl inspect COURSE_URL`
- `swinydl process COURSE_URL`
- `swinydl process-manifest PATH`
- `swinydl download COURSE_URL --media audio|video|both`
- `swinydl transcribe PATH`
- `swinydl doctor`

`swinydl download` remains the command for explicitly retrieving Echo360 media artifacts. `swinydl process` is the normal end-to-end transcript workflow.

For day-to-day use, the simplest entrypoint is:

```bash
./install.sh
```

`install.sh` is the primary supported setup path. In a GitHub DMG release it uses the prebuilt `SWinyDLSafariApp.app`, runs `uv sync`, bootstraps the CoreML bundles, runs `swinydl doctor`, and opens the app plus Safari. In a source checkout, `./install.sh --build-from-source` regenerates the Safari project and builds the app locally.

For a first-time non-technical Mac user, the simplest setup path is:

1. download the latest `SWinyDL-v...dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases)
2. open the DMG and copy the `SWinyDL` folder wherever you want to keep it
3. open Terminal in the copied folder and run `./install.sh`
4. approve the Homebrew and `uv`/`ffmpeg` install prompts if those tools are missing
5. enable `SWinyDL Safari` in Safari Settings

After that:

1. Enable the bundled Safari extension in Safari Settings
2. If it does not appear, enable Safari's Develop menu and turn on `Allow Unsigned Extensions`
3. If you want to verify the extension is registered, run `pluginkit -mAvvv -p com.apple.Safari.web-extension | rg SWinyDL`
4. Open a logged-in Canvas or Echo360 page in Safari
5. Use the extension popup to load the course, choose whether downloaded media should be deleted after transcription, and launch a manifest-driven backend job into the native wrapper app window

The native wrapper window shows per-lesson transcript files and can open the transcription folder directly.
It also shows whether the Parakeet ASR model bundle and speaker diarizer bundle are ready.

The backend has also been verified non-interactively on public sample media:

- local Parakeet CoreML ASR completes unattended
- local CoreML diarization completes unattended
- concurrent transcribes no longer share the same temp workspace or bootstrap state

The old Chrome-guided launcher still exists as fallback:

```bash
uv run app.py
```

Supported scope:

- macOS Apple Silicon
- Safari-first, Chrome fallback
- unsigned GitHub DMG distribution first; signed and notarized distribution is future work
- Python `>=3.11`
- Swift toolchain and xcodegen only for `./install.sh --build-from-source`
- package install via `pip` or `uv`

The old video-downloader implementation, PhantomJS, Firefox, and custom HLS code are intentionally removed from the supported path.

Dependency ranges live in `pyproject.toml`, the tested resolution lives in `uv.lock`, and `swinydl doctor` is only for runtime readiness checks.

GitHub Releases are the update source of truth. Each tagged release should include an unsigned `SWinyDL-v...dmg` built by `.github/workflows/release-dmg.yaml`.

For non-technical users, the preferred update path is to use the app's update check, download the newer DMG, replace the older `SWinyDL` folder, and run `./install.sh` again from that folder. `git pull` remains a technical-user fallback only.

If no GitHub release has been published yet, or if the latest release has no DMG asset, the wrapper app will report that clearly.

There is no separate `requirements.txt` or `MANIFEST.in` workflow in v4.

The transcription stack now uses:

- local Parakeet CoreML via the repo-local Swift runner
- local CoreML speaker diarization via a second Swift runner
- a Safari-native entrypoint that launches `swinydl process-manifest`

`--asr-backend auto` resolves to Parakeet CoreML.

The flow is:

1. Python normalizes media to mono 16 kHz WAV.
2. Python invokes the local Swift runner.
3. Swift loads the staged CoreML Parakeet bundles and runs transcription on Apple Silicon.
4. Swift returns token timings as JSON.
5. Python reconstructs words and transcript segments, then writes `.txt`, `.srt`, and `.json`, with `.txt` treated as the primary human-facing transcript.

Speaker diarization is on by default and runs through the local CoreML diarizer bundles staged under `vendor/speaker-diarization-coreml` or pointed to by `ECHO360_DIARIZER_COREML_DIR`.

Current validation status:

- backend execution is working for unattended local-file transcription
- transcript artifacts are written correctly for `.txt`, `.srt`, and `.json`
- the native wrapper shows stage-level lesson progress, elapsed time, and recent activity from the manifest status sidecar
- concurrency races in bootstrap and temp-workspace handling have been fixed
- live Safari-authenticated Canvas/Echo360 runs still need continued real-world validation
- diarization quality is still tuned for lecture-style media rather than fast two-speaker dialogue

The supported staging path is:

```bash
swinydl bootstrap-models
```

That command downloads the repo-local CoreML bundles from the public Hugging Face sources documented below.

## Model Provenance

The repo runs staged local CoreML bundles, but the update sources are public:

- ASR CoreML pull source: [FluidInference/parakeet-tdt-0.6b-v3-coreml](https://huggingface.co/FluidInference/parakeet-tdt-0.6b-v3-coreml)
- ASR canonical base model: [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- Diarizer CoreML pull source: [FluidInference/speaker-diarization-coreml](https://huggingface.co/FluidInference/speaker-diarization-coreml)
- Diarizer canonical base pipeline: [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

The diarizer bundle corresponds conceptually to:

- segmentation via [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
- speaker embeddings via [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM)
- VBx-style clustering parameters carried by the `community-1` pipeline sidecars

When refreshing models, prefer the CoreML repos for direct staging updates and use the canonical upstream model cards to evaluate architecture or license changes.

The exact staging instructions now live in the root [README](../README.md) and use the built-in `swinydl bootstrap-models` command.
