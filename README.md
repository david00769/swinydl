# SWinyDL

I coded this up in one weekend to help my daughter get transcripts from her lectures she can upload to NotebookLLM

SWinyDL downloads and transcribes Echo360 lecture recordings on Apple Silicon Macs.

It is designed for:
- macOS on Apple Silicon
- Safari as the main browser flow
- lecture-style content with one main speaker and occasional audience questions

Tested on:
- macOS 26.4.1 (`25E253`) on Apple Silicon

## What It Does

SWinyDL lets you:
- open a Canvas or Echo360 page in Safari
- choose which lessons you want
- transcribe them with speaker labels
- watch progress in a small Mac app
- open the finished transcript files directly

The main output is:
- `.txt` for reading

It also writes:
- `.srt` for timed captions
- `.json` for structured transcript data

## Before You Start

You need:
- an Apple Silicon Mac
- Safari
- internet access during setup
- Terminal, only to run the installer

You do not need Xcode or Apple's command line tools for the normal DMG install.

You do not need Swift or local compilation for the normal DMG install. The release DMG includes prebuilt CoreML runner binaries for transcription and speaker separation.

You do not need to install Homebrew, `uv`, or `ffmpeg` before starting. `./install.sh` checks for them and offers to install anything missing.

If you prefer to install Homebrew and the required tools yourself before running SWinyDL, run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install uv ffmpeg
```

## Easiest Install

For most people, the best path is:

1. Download the latest `SWinyDL-v...dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases)
2. Open the DMG
3. Drag the `SWinyDL` folder out of the DMG and put it somewhere you want to keep it, such as `Documents` or `Applications`
4. Do not run the installer from inside the mounted DMG
5. Open Terminal
6. Type `cd ` and drag the copied `SWinyDL` folder into the Terminal window
7. Press `Enter`
8. Run:

```bash
./install.sh
```

If Homebrew, `uv`, or `ffmpeg` are missing, approve the installer prompts.

`./install.sh` does the setup for you:
- offers to install Homebrew if it is missing
- offers to install `uv` and `ffmpeg` if they are missing
- creates the Python environment
- downloads the required local speech models if they are missing
- uses the prebuilt Mac app and Safari extension from the DMG
- uses the prebuilt CoreML runner binaries from the DMG, so transcription does not compile Swift code during normal use
- verifies the Safari extension includes its required `manifest.json`
- ad-hoc signs and verifies the app bundle locally
- registers the containing app and extension with macOS so Safari can list it
- opens the app and Safari when setup is finished

For the normal DMG install, `./install.sh` is still required. It prepares the local Python environment, checks `ffmpeg`, signs and verifies the app bundle, verifies the app can run, and opens Safari so you can enable the extension.

## What Is In The DMG

The DMG is intentionally runtime-only. It includes:
- `SWinyDLSafariApp.app`
- `install.sh`
- the `swinydl` Python runtime package
- prebuilt CoreML runner binaries in `bin/`
- model/runtime assets in `vendor/`
- `WebExtension` for Safari's temporary-extension fallback
- `SWinyDL-WebExtension.zip`, which contains the same temporary-extension files
- license notices and a short runtime install guide

The DMG does not include:
- the Safari Xcode project
- Swift package source
- source-build scripts
- tests
- developer documentation

Build instructions remain on this GitHub page for developers who clone the repository.

You do not need to download the Parakeet model manually.

Do not double-click `SWinyDLSafariApp.app` before running `./install.sh`. This first release is unsigned, and macOS may say the app is damaged if you open it directly from a downloaded DMG. Running `./install.sh` from the copied `SWinyDL` folder clears the downloaded-file quarantine before opening the app.

Do not double-click the embedded `.appex` extension bundle. Safari does not install Safari Web Extensions that way; it discovers the extension through the containing `SWinyDLSafariApp.app`.

## Developer Install

If you want to build SWinyDL from source instead of using the DMG:

1. Install Apple's command line tools if needed:

```bash
xcode-select --install
```

2. Get the source code with either option:

```bash
git clone https://github.com/david00769/swinydl.git
cd swinydl
```

or download and unzip the [source zip](https://github.com/david00769/swinydl/archive/refs/heads/master.zip), then open Terminal in the unzipped folder.

3. Build the Safari app wrapper:

```bash
./scripts/build_app.sh
```

4. Run the installer:

```bash
./install.sh
```

You can also run this shortcut, which builds first and then continues the install:

```bash
./install.sh --build-from-source
```

The source build path:
- offers to install Homebrew if it is missing
- offers to install `uv`, `ffmpeg`, and `xcodegen` if they are missing
- runs `uv sync`
- downloads the required local speech models if they are missing
- runs `scripts/build_app.sh`
- regenerates the Safari Xcode project from `safari/project.yml`
- builds `SWinyDLSafariApp.app` locally with `xcodebuild`
- ad-hoc signs and verifies the locally built app bundle
- runs `swinydl doctor`
- opens the newly built app and Safari

Xcode command line tools, `xcodegen`, and local compilation are only needed for this developer source-build path. Normal DMG users do not need them.

If you already have a prebuilt `SWinyDLSafariApp.app` in the folder but still want to force a local rebuild, use `./scripts/build_app.sh` or `./install.sh --build-from-source`.

## First Run

After the installer finishes:

1. Open Safari `Settings > Advanced`
2. Turn on `Show features for web developers`
3. Open Safari `Settings > Developer`
4. Turn on `Allow unsigned extensions` and enter your Mac password when prompted
5. Open Safari `Settings > Extensions`
6. Enable `SWinyDL Safari`
7. If it still does not appear, quit and reopen `SWinyDLSafariApp.app` from the copied `SWinyDL` folder, or run `./install.sh` again
8. If it still does not appear after that, use the temporary extension fallback below
9. Open your Canvas or Echo360 page in Safari
10. Open the `SWinyDL Safari` extension
11. Choose the lessons you want
12. Start the job

Because this first release is unsigned, Safari may require developer-mode extension loading. Apple's unsigned-extension setting resets every time Safari quits, so you may need to turn on `Allow unsigned extensions` again after restarting Safari.

Temporary extension fallback:

1. Open Safari `Settings > Developer`
2. Turn on `Allow unsigned extensions`
3. Click `Add Temporary Extension...`
4. In the file picker, go to your copied `SWinyDL` folder
5. Select this folder, but do not open it:

```text
WebExtension
```

6. Click `Select`
7. Enable the temporary `SWinyDL Safari` extension in Safari `Settings > Extensions`

If you cannot select the `WebExtension` folder, select this zip file in the same copied `SWinyDL` folder instead:

```text
SWinyDL-WebExtension.zip
```

Do not select `SWinyDLSafariApp.app`, `SWinyDLSafariExtension.appex`, or `manifest.json` for this temporary-extension fallback. Safari wants the folder or zip file that contains `manifest.json`.

Safari removes temporary extensions after 24 hours or when you quit Safari. If you use this fallback, repeat the `Add Temporary Extension...` step after every Safari restart.

The Mac app will show:
- whether the models are ready
- which lessons are queued or running
- percent progress and current stage
- when each transcript is complete
- links to open the transcript or the transcript folder

## What You Get

For each completed lesson, SWinyDL writes:
- `.txt` transcript
- `.srt` subtitle file
- `.json` structured transcript

In the app, `.txt` is treated as the main transcript file.

By default, SWinyDL deletes downloaded audio or video after transcription to save disk space. You can turn that off in the Safari popup before launching a job.

## Updating

The simplest update path is:

1. In the app, choose `Check for Updates`
2. If a newer release is available, click `Download DMG`
3. Open the downloaded DMG from Downloads
4. Quit SWinyDL
5. Drag the new `SWinyDL` folder out of the DMG
6. Replace the older `SWinyDL` folder with the newer one
7. Open Terminal in the new copied folder
8. Run:

```bash
./install.sh
```

You can also download the latest DMG manually from [GitHub Releases](https://github.com/david00769/swinydl/releases).

## Troubleshooting

### The Safari extension does not appear

1. Run `./install.sh` again
2. Open Safari `Settings > Advanced` and turn on `Show features for web developers`
3. Open Safari `Settings > Developer` and turn on `Allow unsigned extensions`
4. Open Safari `Settings > Extensions`
5. Enable `SWinyDL Safari`
6. If the extension still does not appear, quit and reopen `SWinyDLSafariApp.app` from the copied `SWinyDL` folder, or run `./install.sh` again so it re-registers the extension
7. If the extension still does not appear, use Safari `Settings > Developer > Add Temporary Extension...` and select the `WebExtension` folder from your copied `SWinyDL` folder without opening it
8. If the file picker will not let you select that folder, select `SWinyDL-WebExtension.zip` from the same copied `SWinyDL` folder

Do not double-click `SWinyDLSafariExtension.appex`; macOS may warn that it is unsigned, and Safari will not install it directly. The app bundle contains the extension and registers it with Safari when the app opens.

Temporary extensions are not permanent. Safari removes them after 24 hours or when Safari quits, so repeat `Add Temporary Extension...` after each Safari restart until SWinyDL ships as a signed/notarized app.

You can also check app health in Terminal:

```bash
swinydl doctor
```

### macOS says the app is damaged

Make sure you copied the `SWinyDL` folder out of the DMG, then run:

```bash
./install.sh
```

The installer locally signs the bundled app, clears downloaded-file quarantine, then opens it. Do not run the app directly from inside the mounted DMG.

### The app says models are missing

Run:

```bash
./install.sh
```

or:

```bash
swinydl bootstrap-models
```

### A run looks slow

Large lectures can sit in one stage for a while during local transcription or diarization. The app should still show the current stage, elapsed time, and recent activity.

If something looks wrong, run:

```bash
swinydl doctor
```

## Technical Fallbacks

If you are comfortable with the command line, the runtime DMG still includes the `swinydl` CLI:

```bash
swinydl process COURSE_URL
swinydl process-manifest /path/to/job.json
swinydl transcribe /path/to/local/file.mp4
```

The older Chrome-guided launcher is a developer/source-checkout fallback only. It is not included in the runtime DMG:

```bash
uv run app.py
```

## More Detail

If you want source-build instructions, lower-level technical notes, commands, and model details, see the GitHub repository:
- [docs/index.md](docs/index.md)
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
