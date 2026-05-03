# SWinyDL v4

See the repository root [README](../README.md) for the supported install and usage flow, and see the [user guide](user-guide.md) for the click-by-click normal-user workflow.

The v4 line is transcript-first:

- Safari wrapper app + Safari Web Extension
- `uv run swinydl inspect COURSE_URL`
- `uv run swinydl process COURSE_URL`
- `uv run swinydl process-manifest PATH`
- `uv run swinydl download COURSE_URL --media audio|video|both`
- `uv run swinydl transcribe PATH`
- `uv run swinydl doctor`

Run those commands from the source checkout or copied `SWinyDL` folder after setup. `uv run swinydl download` retrieves Echo360 media files explicitly. `uv run swinydl process` is the normal end-to-end transcript workflow.

For day-to-day use, the simplest entrypoint is:

Open `SWinyDLSafariApp.app` from the copied GitHub DMG folder, choose an output folder, then use Safari to queue jobs.

`install.sh` remains the Terminal-owned setup and repair implementation. In a GitHub DMG release it uses the prebuilt `SWinyDLSafariApp.app` and prebuilt transcription helper programs, verifies the Safari extension files, runs `uv sync`, downloads the local speech models if they are missing, locally re-signs and verifies the app bundle, registers the app and extension with macOS, runs the doctor check, and opens the app plus Safari. The app's `Copy Repair Command` button copies the Terminal command; it does not run `install.sh` inside the sandbox. Use Terminal `./install.sh` if the app cannot launch, if Homebrew, `uv`, or `ffmpeg` need interactive installation, or if setup needs repair. `Copy Log Path` copies the app-group logs folder path, and `Export Diagnostics` creates a sanitized diagnostics zip. In a source checkout, `./install.sh` does not compile the Safari wrapper by default; use `./scripts/build_app.sh` first, or use `./install.sh --build-from-source` as a compatibility shortcut. For unsigned DMG installs, it also clears downloaded-file quarantine from the bundled app before opening it.

The GitHub DMG is runtime-only. It includes install/runtime files, the prebuilt app, the WebExtension resources needed for Safari's temporary-extension fallback, the Python runtime package, an empty/staging `vendor/` folder for local speech models, and license notices. It intentionally does not include the Safari Xcode project, Swift package source, test suite, or build scripts. Developer build instructions remain in the GitHub repository.

First download checklist for a non-technical Mac user:

1. download the latest `SWinyDL-v...dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases)
2. open the DMG
3. drag the `SWinyDL` folder out of the DMG and put it somewhere writable, such as `Desktop` or `Documents`
4. Open the unsigned app from Finder: Control-click or right-click `SWinyDLSafariApp.app`, choose `Open`, and confirm the warning. If that is awkward on the trackpad, select the app and choose Finder `File > Open`.
5. choose an output folder in the app if the Readiness panel asks for one
6. if setup, Safari registration, signing, or models need repair, click `Copy Repair Command`, paste the command into Terminal, and press `Enter`
7. if macOS asks whether `SWinyDLSafariApp` can access data from other apps, click `Allow` so the Safari handoff queue works
8. if the app cannot open, open Terminal in the copied folder and run `./install.sh`
9. if Terminal says permission is denied, run `chmod +x install.sh` and then `./install.sh` again
10. enable `SWinyDL Safari` in Safari Settings

Terminal fallback is for unsigned-app launch failures, command-line dependencies, signing or Safari registration repair, and model setup.

If macOS blocks the unsigned app, use Finder to open it: Control-click or right-click `SWinyDLSafariApp.app`, choose `Open`, and confirm the warning. The equivalent menu path is to select `SWinyDLSafariApp.app` and choose Finder `File > Open`. If macOS still blocks it or says the app is damaged, run `./install.sh` from the copied folder.

If `./install.sh` says the folder is missing runtime files, or `uv` reports `No module named 'swinydl'`, delete the copied `SWinyDL` folder and download the latest DMG again. A complete runtime folder includes the `swinydl` Python runtime package and the `bin/` runner binaries.

If Terminal shows `Library/Containers/.../Data/Desktop/SWinyDL/install.sh: Operation not permitted`, the command is using a sandbox-rewritten path. Open Terminal yourself, type `cd `, drag the real copied `SWinyDL` folder from Finder into Terminal, press `Enter`, then run `./install.sh`.

After that:

1. Open Safari `Settings > Advanced` and turn on `Show features for web developers`
2. Open Safari `Settings > Developer` and turn on `Allow unsigned extensions`
3. Open Safari `Settings > Extensions` and enable `SWinyDL Safari`
4. If it still does not appear, quit and reopen `SWinyDLSafariApp.app` from the copied `SWinyDL` folder, or run `./install.sh` again
5. If needed, use Safari `Settings > Developer > Add Temporary Extension...`, select the `WebExtension` folder from the copied `SWinyDL` folder without opening it, and click `Select`
6. If the picker will not let you select that folder, select `SWinyDL-WebExtension.zip` from the same copied `SWinyDL` folder instead
7. If you want to verify the extension is registered, run `pluginkit -mAvvv -p com.apple.Safari.web-extension | rg SWinyDL`
8. Open a logged-in Canvas or Echo360 page in Safari
9. Use `Open App` in the extension popup to bring the native wrapper window forward
10. Use the extension popup to load the course, choose whether downloaded media should be deleted after transcription, and launch the transcription job into the native app window

The normal first-transcript flow is documented in [docs/user-guide.md](user-guide.md). In short: open the app, choose an output folder, click `Allow` if macOS asks whether SWinyDL can access data from other apps, run the copied Terminal repair command only if setup needs repair, open a logged-in Canvas or EchoVideo page, use the Safari popup's `Reload`, `Check All`, `Uncheck All`, `Transcribe`, and `Download + Transcribe` controls, then watch the persistent popup handoff: `Queued for transcription. Progress appears in SWinyDL.` If the app does not open, the popup says `Queued, but SWinyDL did not open. Click Open App.`

Do not double-click `SWinyDLSafariExtension.appex`. Safari discovers the extension through the containing `SWinyDLSafariApp.app`; `./install.sh` also re-registers that containing app and extension with macOS.

The temporary extension fallback is not permanent. Safari removes temporary extensions after 24 hours or when Safari quits, and Safari's `Allow unsigned extensions` setting also resets when Safari quits. If you rely on `Add Temporary Extension...`, repeat that step after each Safari restart until SWinyDL ships as a signed/notarized app.

The native wrapper window shows whether Safari handoff is ready, shared queue status, whether the Parakeet ASR model bundle and speaker diarizer bundle are ready, per-lesson transcript files, and the saved output folder. Choose the transcript folder with `Defaults > Output folder > Choose` in the native app; Safari-launched jobs use that saved native-app setting. Jobs stay pending until an output folder is selected. `Open Outputs` shows and opens the current saved folder. Runtime scratch files, backend logs, job manifests, and debug exports live in the app-group container, not in guessed Desktop paths.

If course discovery fails, click `Export Debug Log` in the Safari extension popup. SWinyDL saves a sanitized JSON file in the app-group `DebugExports` folder, with a Downloads fallback only if macOS permits it. Share that JSON file; it includes page/discovery state but excludes cookies, storage values, hidden input values, and full raw HTML.

The backend has also been verified non-interactively on public sample media:

- local Parakeet CoreML ASR completes unattended
- local CoreML diarization completes unattended
- concurrent transcribes no longer share the same temp workspace or bootstrap state

The old Chrome-guided launcher exists only in source checkouts. It is not included in the runtime DMG:

```bash
uv run app.py
```

Supported scope:

- macOS Apple Silicon
- Safari-first, Chrome fallback
- unsigned GitHub DMG distribution first; signed and notarized distribution is future work
- Python `>=3.11`
- Swift toolchain and xcodegen only for source checkouts and `./install.sh --build-from-source`
- package install via `pip` or `uv`

## Building From Source

The normal user path is the GitHub DMG. Source builds are for developers who want to modify or inspect the Safari wrapper, backend, or release packaging.

Source-build prerequisites:

- Apple Silicon Mac
- Safari
- internet access
- Apple's command line tools, installed with `xcode-select --install` if needed
- Homebrew, `uv`, `ffmpeg`, and `xcodegen`; `./install.sh --build-from-source` can offer to install these with Homebrew

Clone the repo:

```bash
git clone https://github.com/david00769/swinydl.git
cd swinydl
```

Then build the Safari app wrapper:

```bash
./scripts/build_app.sh
```

Then run the installer:

```bash
./install.sh
```

`scripts/build_app.sh` regenerates `safari/SWinyDLSafari.xcodeproj` from `safari/project.yml`, builds `SWinyDLSafariApp.app` with `xcodebuild`, and locally re-signs and verifies the app bundle. `install.sh` then runs `uv sync`, downloads the local speech models if they are missing, verifies the app bundle, runs the doctor check, then opens the app and Safari.

As a shortcut, developers can run:

```bash
./install.sh --build-from-source
```

If you downloaded a source zip instead of cloning, unzip it, open Terminal in the unzipped folder, and run the same build/install commands.

The old video-downloader implementation, PhantomJS, Firefox, and custom HLS code are intentionally removed from the supported path.

Dependency ranges live in `pyproject.toml`, the tested resolution lives in `uv.lock`, and `uv run swinydl doctor` is only for runtime readiness checks.

GitHub Releases are the update source of truth. Each tagged release should include an unsigned `SWinyDL-v...dmg` built by `.github/workflows/release-dmg.yaml`.

For non-technical users, the preferred update path is to use the app's update check, download the newer DMG, drag the new `SWinyDL` folder out of the DMG, replace the older `SWinyDL` folder, then run `./install.sh` from Terminal in the copied folder. `git pull` remains a technical-user fallback only.

If no GitHub release has been published yet, or if the latest release has no DMG asset, the wrapper app will report that clearly.

There is no separate `requirements.txt` or `MANIFEST.in` workflow in v4.

The transcription stack now uses:

- local Parakeet CoreML via the packaged runner binaries in the runtime DMG, or the repo-local Swift package in source checkouts
- local CoreML speaker diarization via the packaged runner binaries in the runtime DMG, or the repo-local Swift package in source checkouts
- a Safari-native entrypoint that launches the same workflow as `uv run swinydl process-manifest`

`--asr-backend auto` resolves to Parakeet CoreML.

The flow is:

1. Python normalizes media to mono 16 kHz WAV.
2. Python invokes the packaged runner binary from `bin/` in a runtime DMG install, or builds and invokes the source runner in a developer checkout.
3. The runner loads the staged CoreML Parakeet bundles and runs transcription on Apple Silicon.
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
uv run swinydl bootstrap-models
```

Run that command from the copied `SWinyDL` folder or source checkout after setup. It downloads the local speech model bundles from the public Hugging Face sources documented below. The Safari app exposes `Copy Repair Command` in the `Readiness` panel so users can paste the correct Terminal repair command without learning the copied-folder path.

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

The exact staging instructions now live in the root [README](../README.md) and use the built-in `uv run swinydl bootstrap-models` command.
