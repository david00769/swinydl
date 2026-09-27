# SWinyDL User Guide

This guide walks through the normal install from the GitHub DMG and your first transcripts. You do not need Xcode, Swift or any local compilation.

You need a Mac with Apple Silicon, Safari and an internet connection.

## 1. Copy the Folder

1. Download the latest `SWinyDL-v...dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases).
2. Open the DMG.
3. Drag the `SWinyDL` folder out of the DMG to a normal folder such as `Documents`.
4. Do not run anything from inside the mounted DMG.

## 2. Run Setup

1. Open Terminal.
2. Type `cd ` (with a trailing space), drag the copied `SWinyDL` folder into Terminal, then press `Enter`.
3. Run:

```bash
./install.sh
```

4. If the installer offers to install Homebrew, `uv` or `ffmpeg`, approve it.

If Terminal says `permission denied`, run:

```bash
chmod +x install.sh
./install.sh
```

Setup creates the Python environment, downloads the speech models, signs the app for your Mac, registers the Safari extension, and opens the app and Safari.

## 3. Enable the Safari Extension

1. Open Safari `Settings > Advanced`.
2. Turn on `Show features for web developers`.
3. Open Safari `Settings > Developer`.
4. Turn on `Allow unsigned extensions` and enter your Mac password.
5. Open Safari `Settings > Extensions`.
6. Enable `SWinyDL Safari`.

Safari turns `Allow unsigned extensions` off whenever it quits. Repeat steps 3 to 6 after each Safari restart.

If `SWinyDL Safari` is not listed, quit and reopen `SWinyDLSafariApp.app` from the copied folder, or run `./install.sh` again. If it is still missing, use the temporary extension below.

## 4. Set Up the App

1. Open `SWinyDLSafariApp.app` from the copied `SWinyDL` folder. If macOS blocks it, Control-click or right-click the app, choose `Open`, then confirm. You can also select the app and choose Finder `File > Open`.
2. Choose an output folder. Jobs wait until one is chosen.
3. If macOS asks whether `SWinyDLSafariApp` can access data from other apps, click `Allow`. This lets the extension pass jobs to the app.
4. Check the `Readiness` panel. `Safari handoff`, `Parakeet ASR`, `Speaker diarizer` and `Output folder` should all be ready.

## 5. Transcribe Lessons

1. In Safari, sign in to Canvas or Echo360.
2. Open the course page or Echo360 page that lists the lectures.
3. Click the `SWinyDL Safari` button in the Safari toolbar.
4. Click `Reload` if the lesson list looks stale.
5. Choose lessons, or use `Check All` and `Uncheck All`.
6. Click `Transcribe` for transcripts only.
7. To keep the lesson media as well, turn off `Delete downloaded media after transcription` and click `Download + Transcribe`. With the checkbox on, the media is deleted after transcription either way.
8. The popup shows `Queued for transcription.` If the app did not open, it shows `Queued, but SWinyDL did not open.` Click `Open App`.

The app shows each job's lessons, progress, current stage, elapsed time and any errors.

## 6. Open Your Transcripts

For each lesson, SWinyDL writes:

- `.txt`, the main transcript
- `.srt`, timed captions
- `.json`, structured transcript data

They go to the output folder you chose. To change it, use `Defaults > Output folder` in the app: `Choose` picks a new folder, `Open` shows it in Finder, and `Reset` clears it.

Completed lessons have buttons such as `Open Transcript` and `Open Folder`. `Open Outputs` in the `Workspace` panel opens the output folder.

Temporary downloads and converted audio stay in the app's own storage, not in your output folder. SWinyDL deletes them after each lesson unless you chose to keep media.

## Temporary Extension

Use this only if `SWinyDL Safari` does not appear in Safari `Settings > Extensions`.

1. Open Safari `Settings > Developer`.
2. Turn on `Allow unsigned extensions`.
3. Click `Add Temporary Extension...`.
4. Go to the copied `SWinyDL` folder and select the `WebExtension` folder. Do not open it.
5. Click `Select`.
6. Enable the temporary `SWinyDL Safari` extension in Safari `Settings > Extensions`.

If Safari will not let you select the `WebExtension` folder, select `SWinyDL-WebExtension.zip` from the same folder.

Do not select `SWinyDLSafariApp.app`, `SWinyDLSafariExtension.appex` or `manifest.json`.

Safari removes temporary extensions after 24 hours or when it quits. Repeat these steps after each Safari restart.

If an older temporary extension says an EchoVideo page is unsupported, remove it in Safari `Settings > Extensions` and add the current `WebExtension` folder or zip again.

## Updating

1. In the app, choose `Check for Updates`.
2. If a newer release exists, click `Download DMG`. SWinyDL saves it to Downloads and opens it.
3. Quit SWinyDL.
4. Drag the new `SWinyDL` folder out of the DMG and replace the old copied folder.
5. Run setup from Terminal in the new folder:

```bash
./install.sh
```

Replacing the folder is not enough on its own. `./install.sh` refreshes the Python environment, app signing, Safari registration and models.

## Quick Fixes

The app's `Diagnostics` panel has:

- `Copy Repair Command`: copies a Terminal command that runs `./install.sh` from your copied folder. Paste it into Terminal and press `Enter`. The app cannot run the installer itself.
- `Copy Log Path`: copies the path of the logs folder.
- `Export Diagnostics`: saves a diagnostics zip to share when you report a problem.

**The app says models are missing.** Run the repair command.

**macOS says the app is damaged or will not open it.** Make sure you copied the `SWinyDL` folder out of the DMG, then run `./install.sh` from the copied folder.

**The installer says runtime files are missing**, or `uv` reports `No module named 'swinydl'`. Delete the copied folder, download the latest DMG and copy the folder out again.

**Terminal says `Operation not permitted`** for a path like `Library/Containers/.../Data/Desktop/SWinyDL/install.sh`. Open Terminal yourself, type `cd `, drag the real copied `SWinyDL` folder from Finder into Terminal, press `Enter`, then run `./install.sh`.

**The extension disappeared after Safari restarted.** Turn `Allow unsigned extensions` back on, or add the temporary extension again.

**A course page does not load, or no lessons appear.** Make sure you have the latest release, then click `Export Debug Log` in the extension popup. It saves a file named like `swinydl-debug-YYYYMMDD-HHMMSS.json` in the app's `DebugExports` folder. The file describes the page and what SWinyDL found. It leaves out cookies, stored page values, hidden form values and the full page HTML. Share that file when you report the problem.

More help and the command line tool are described at [github.com/david00769/swinydl](https://github.com/david00769/swinydl).
