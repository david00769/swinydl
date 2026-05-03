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
- Terminal only if macOS will not open the unsigned app, or if setup repair reports missing command-line tools

You do not need Xcode or Apple's command line tools for the normal DMG install.

You do not need Swift or local compilation for the normal DMG install. The release DMG includes prebuilt CoreML runner binaries for transcription and speaker separation.

You do not need to install Homebrew, `uv`, or `ffmpeg` before opening SWinyDL. If the app's `Repair Setup` action cannot find them, run `./install.sh` from Terminal and approve its install prompts.

If you prefer to install Homebrew and the required tools yourself before running SWinyDL, run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install uv ffmpeg
```

## Easiest Install

First download checklist:

For most people, the best path is:

1. Download the latest `SWinyDL-v...dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases)
2. Open the DMG
3. Drag the `SWinyDL` folder out of the DMG and put it somewhere you want to keep it, such as `Documents` or `Applications`
4. Do not run anything from inside the mounted DMG
5. Control-click `SWinyDLSafariApp.app` in the copied folder, choose `Open`, then confirm the unsigned-app warning
6. Click `Repair Setup` in the app's `Readiness` panel if setup, Safari registration, or model checks need repair
7. If macOS asks whether `SWinyDLSafariApp` can access data from other apps, click `Allow`. That lets the Safari extension and app share queued jobs.
8. If `Repair Setup` reports missing Homebrew, `uv`, or `ffmpeg`, or if macOS will not open the unsigned app at all, use the Terminal fallback below

Terminal fallback:

1. Open Terminal
2. Type `cd ` and drag the copied `SWinyDL` folder into the Terminal window
3. Press `Enter`
4. Run:

```bash
./install.sh
```

The release DMG should already make `install.sh` executable. If Terminal still says `permission denied`, make the installer executable and run it again:

```bash
chmod +x install.sh
./install.sh
```

If Homebrew, `uv`, or `ffmpeg` are missing, approve the installer prompts.

If macOS blocks the unsigned app after setup, prefer Control-clicking `SWinyDLSafariApp.app`, choosing `Open`, then confirming the warning. Do not open the app from inside the mounted DMG.

`Repair Setup` in the app runs the non-interactive repair path from `install.sh`. The Terminal installer remains the fallback when the app cannot launch or dependencies need interactive installation. `./install.sh` does the setup for you:
- offers to install Homebrew if it is missing
- offers to install `uv` and `ffmpeg` if they are missing
- creates the Python environment
- downloads the required local speech models if they are missing
- uses the prebuilt Mac app and Safari extension from the DMG
- uses the prebuilt CoreML runner binaries from the DMG, so transcription does not compile Swift code during normal use
- verifies the Safari extension includes its required `manifest.json`
- ad-hoc signs and verifies the app bundle locally
- registers the containing app and extension with macOS so Safari can list it
- opens the app and Safari when setup is finished, unless the app launched it in repair mode

For the normal DMG install, `./install.sh` is no longer the first thing to try if the app opens. `Repair Setup` is always available in the app's `Readiness` panel. Use it first; run `./install.sh` manually when the app cannot open, when command-line dependencies need interactive installation, or when you want a Terminal repair log.

After a repair run, use `Open Logs` in the same `Readiness` panel to inspect setup output.

Signing and notarization are the future fix for removing the remaining Control-click or Terminal fallback.

## What Is In The DMG

The DMG is intentionally runtime-only. It includes:
- `SWinyDLSafariApp.app`
- `install.sh`
- the `swinydl` Python runtime package
- prebuilt CoreML runner binaries in `bin/`
- model/runtime assets in `vendor/`
- `WebExtension` for Safari's temporary-extension fallback
- `SWinyDL-WebExtension.zip`, which contains the same temporary-extension files
- `USER-GUIDE.md`, the normal-user click-by-click guide
- license notices and a short runtime install guide

The DMG does not include:
- the Safari Xcode project
- Swift package source
- source-build scripts
- tests
- developer documentation

Build instructions remain on this GitHub page for developers who clone the repository.

You do not need to download the Parakeet model manually.

Do not open `SWinyDLSafariApp.app` from inside the mounted DMG. This first release is unsigned, so macOS may block the first launch. Copy the folder out first, then Control-click `SWinyDLSafariApp.app` and choose `Open`. If macOS still says the app is damaged, run `./install.sh` from the copied `SWinyDL` folder to clear quarantine and repair local signing.

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
11. Use `Open App` in the extension popup if you need to bring the full SWinyDL app window forward
12. Choose the lessons you want
13. Start the job

The full app entry point is either the `Open App` button in the Safari extension popup or `SWinyDLSafariApp.app` inside your copied `SWinyDL` folder. The app window shows model readiness, queued jobs, progress, and transcript output links.

If a page does not load as expected, click `Export Debug Log` in the Safari extension popup. It saves one sanitized JSON file with page/discovery details and no cookies or full raw HTML.

Because this first release is unsigned, Safari may require developer-mode extension loading. Apple's unsigned-extension setting resets every time Safari quits, so you may need to turn on `Allow unsigned extensions` again after restarting Safari.

For a fuller click-by-click walkthrough, see the [user guide](docs/user-guide.md).

## First Transcript Checklist

1. Open `SWinyDLSafariApp.app` from the copied `SWinyDL` folder.
2. Click `Repair Setup` in the `Readiness` panel if setup or models need repair.
3. If the Readiness panel shows `Safari handoff` as needing attention, allow the macOS app-data prompt when it appears.
4. Open a logged-in Canvas or EchoVideo lecture page in Safari.
5. Open the `SWinyDL Safari` extension popup.
6. Click `Reload` if needed.
7. Use `Check All` or `Uncheck All`, then choose the lessons you want.
8. Leave `Delete downloaded media after transcription` on unless you want to keep media files.
9. Click `Transcribe`, or click `Download + Transcribe` if you want the media retained during the run.
10. The popup shows a persistent handoff message: `Queued for transcription. Progress appears in SWinyDL.`
11. If the app does not appear, the popup says `Queued, but SWinyDL did not open. Click Open App.`
12. Watch progress in the app and open finished `.txt` transcripts from the job card.

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
- whether Safari handoff is ready
- the shared queue status, such as `Ready - No queued jobs` or `Ready - 2 queued jobs`
- whether the models are ready
- the saved transcript output folder
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

The default output folder is `swinydl-output` inside the copied `SWinyDL` folder. To choose a different folder, open the native app and use `Defaults > Output folder > Choose`. SWinyDL saves that folder for future Safari-launched jobs. The `Open Outputs` row shows the current folder name and opens the saved folder even before the first job completes. Completed jobs also show transcript and folder buttons.

Temporary downloads, converted audio, and cookie handoff files use the `temp` folder inside the same copied `SWinyDL` folder. SWinyDL removes per-lesson temporary media after transcription unless you choose to retain media.

By default, SWinyDL deletes downloaded audio or video after transcription to save disk space. You can turn that off in the Safari popup before launching a job.

## Updating

The simplest update path is:

1. In the app, choose `Check for Updates`
2. If a newer release is available, click `Download DMG`
3. Open the downloaded DMG from Downloads
4. Quit SWinyDL
5. Drag the new `SWinyDL` folder out of the DMG
6. Replace the older `SWinyDL` folder with the newer one
7. Open `SWinyDLSafariApp.app` from the new copied folder
8. Click `Repair Setup` in the `Readiness` panel if setup or models need repair
9. If the app cannot open, use Terminal in the new copied folder and run `./install.sh`

You can also download the latest DMG manually from [GitHub Releases](https://github.com/david00769/swinydl/releases).

## Troubleshooting

### The Safari extension does not appear

1. Open `SWinyDLSafariApp.app` and click `Repair Setup` in the `Readiness` panel
2. Open Safari `Settings > Advanced` and turn on `Show features for web developers`
3. Open Safari `Settings > Developer` and turn on `Allow unsigned extensions`
4. Open Safari `Settings > Extensions`
5. Enable `SWinyDL Safari`
6. If the extension still does not appear, quit and reopen `SWinyDLSafariApp.app`, then click `Repair Setup` again so it re-registers the extension
7. If the extension still does not appear, use Safari `Settings > Developer > Add Temporary Extension...` and select the `WebExtension` folder from your copied `SWinyDL` folder without opening it
8. If the file picker will not let you select that folder, select `SWinyDL-WebExtension.zip` from the same copied `SWinyDL` folder

Do not double-click `SWinyDLSafariExtension.appex`; macOS may warn that it is unsigned, and Safari will not install it directly. The app bundle contains the extension and registers it with Safari when the app opens.

Temporary extensions are not permanent. Safari removes them after 24 hours or when Safari quits, so repeat `Add Temporary Extension...` after each Safari restart until SWinyDL ships as a signed/notarized app.

If you installed an older temporary extension and EchoVideo still says the page is unsupported, remove the old temporary extension from Safari `Settings > Extensions`, then add the current `SWinyDL-WebExtension.zip` or `WebExtension` folder again. The current extension needs permission for `echo360.net.au`, which older temporary installs did not request.

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

### Signing fails with resource fork or Finder information

If `./install.sh` fails with `resource fork, Finder information, or similar detritus not allowed`, download the latest release and run `./install.sh` again. Current installers scrub that metadata before signing.

For an older copied folder, this manual cleanup also works:

```bash
/usr/bin/dot_clean -m SWinyDLSafariApp.app
/usr/bin/xattr -cr SWinyDLSafariApp.app
./install.sh
```

### The app says models are missing

Click `Repair Setup` in the app's `Readiness` panel. The app runs the non-interactive installer repair path, refreshes model readiness, repairs local signing, and re-registers the Safari extension. If repair fails, click `Open Logs` in the same panel.

If you prefer Terminal, run:

```bash
swinydl bootstrap-models
```

Running the installer again also repairs the local model folder:

```bash
./install.sh
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
- [docs/user-guide.md](docs/user-guide.md)
- [docs/index.md](docs/index.md)
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
