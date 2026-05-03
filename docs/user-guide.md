# SWinyDL User Guide

This guide is for the normal GitHub DMG install. It does not require Xcode, xcodegen, Swift, or source compilation.

## First Download

First download checklist:

1. Download the latest `SWinyDL-v...dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases).
2. Open the DMG.
3. Drag the `SWinyDL` folder out of the DMG to a normal folder such as `Documents` or `Applications`.
4. Do not run anything from inside the mounted DMG.
5. Control-click `SWinyDLSafariApp.app`, choose `Open`, then confirm the unsigned-app warning.
6. Click `Repair Setup` in the app's `Readiness` panel if setup, Safari registration, or model checks need repair.
7. If macOS asks whether `SWinyDLSafariApp` can access data from other apps, click `Allow`. That permission lets the Safari extension and app share queued jobs.

Terminal fallback:

Use this if macOS will not open the unsigned app, or if `Repair Setup` reports missing Homebrew, `uv`, or `ffmpeg`.

1. Open Terminal.
2. Type `cd `, drag the copied `SWinyDL` folder into Terminal, then press `Enter`.
3. Run:

```bash
./install.sh
```

The release DMG should already make `install.sh` executable. If Terminal says `permission denied`, run:

```bash
chmod +x install.sh
./install.sh
```

Approve the installer prompts if Homebrew, `uv`, or `ffmpeg` are missing. The installer uses the prebuilt app and prebuilt CoreML runner binaries from the DMG.

If macOS blocks the unsigned app after setup, Control-click `SWinyDLSafariApp.app`, choose `Open`, then confirm the warning. If macOS says the app is damaged, run `./install.sh` from the copied folder.

Signing and notarization are the future fix for removing the remaining Control-click or Terminal fallback.

## Enable Safari

1. Open Safari `Settings > Advanced`.
2. Turn on `Show features for web developers`.
3. Open Safari `Settings > Developer`.
4. Turn on `Allow unsigned extensions`.
5. Open Safari `Settings > Extensions`.
6. Enable `SWinyDL Safari`.

If `SWinyDL Safari` does not appear, quit and reopen `SWinyDLSafariApp.app` from the copied `SWinyDL` folder, or run `./install.sh` again.

## Temporary Extension Fallback

Use this only if the normal Safari extension does not appear.

1. Open Safari `Settings > Developer`.
2. Turn on `Allow unsigned extensions`.
3. Click `Add Temporary Extension...`.
4. Select the `WebExtension` folder inside the copied `SWinyDL` folder, but do not open the folder.
5. Click `Select`.
6. Enable the temporary `SWinyDL Safari` extension in Safari `Settings > Extensions`.

If Safari will not let you select the `WebExtension` folder, select `SWinyDL-WebExtension.zip` from the same copied `SWinyDL` folder.

Do not select `SWinyDLSafariApp.app`, `SWinyDLSafariExtension.appex`, or `manifest.json`. Safari wants the folder or zip file that contains `manifest.json`.

Safari removes temporary extensions after 24 hours or when Safari quits. Safari also resets `Allow unsigned extensions` when Safari quits, so repeat these steps after each Safari restart while SWinyDL is unsigned.

## First Transcript

1. Open `SWinyDLSafariApp.app` from the copied `SWinyDL` folder.
2. Click `Repair Setup` in the `Readiness` panel if setup or models need repair.
3. Confirm the `Safari handoff` row is ready. If macOS asks whether SWinyDL can access data from other apps, click `Allow`.
4. Open Safari and sign in to Canvas or EchoVideo.
5. Open the course page or EchoVideo page that lists lectures.
6. Click the `SWinyDL Safari` extension button in Safari.
7. Click `Reload` if the popup has stale page state.
8. Use `Check All` or `Uncheck All`, then choose the lessons you want.
9. Leave `Delete downloaded media after transcription` on unless you want to keep the downloaded media files.
10. Click `Transcribe` for transcripts only, or `Download + Transcribe` if you also want SWinyDL to retain the media during the run.
11. The popup shows `Queued for transcription. Progress appears in SWinyDL.`
12. If the app does not appear, the popup says `Queued, but SWinyDL did not open. Click Open App.`

The app window shows Safari handoff readiness, shared queue status, queued jobs, running progress, current stage, elapsed time, errors, and links to finished transcript files.

## Outputs

For each completed lesson, SWinyDL writes:

- `.txt` as the primary transcript
- `.srt` for timed captions
- `.json` for structured transcript data

The default output folder is `swinydl-output` inside the copied `SWinyDL` folder. To choose a different transcript folder, use `Defaults > Output folder > Choose` in the native app. SWinyDL saves that folder for future Safari-launched jobs. The `Open Outputs` row shows the current folder name and opens that saved folder. Use `Open Transcript` or `Open Folder` from completed job rows to get to specific files.

Temporary downloads, converted audio, and cookie handoff files use the `temp` folder inside the same copied `SWinyDL` folder. SWinyDL removes per-lesson temporary media after transcription unless you choose to retain media.

## Debug Export

If SWinyDL does not recognize a course page or cannot discover lessons, click `Export Debug Log` in the Safari extension popup.

That saves one sanitized JSON file named like `swinydl-debug-YYYYMMDD-HHMMSS.json`. It includes page/discovery state and excludes cookies, storage values, hidden input values, bearer/session tokens, and full raw HTML.

## Updating

1. In the app, choose `Check for Updates`.
2. If a newer release is available, click `Download DMG`.
3. Open the downloaded DMG.
4. Quit SWinyDL.
5. Drag the new `SWinyDL` folder out of the DMG.
6. Replace the older copied `SWinyDL` folder.
7. Open `SWinyDLSafariApp.app` from the new copied folder.
8. Click `Repair Setup` in the `Readiness` panel if setup or models need repair.
9. If the app cannot open, use Terminal in the new copied folder and run:

```bash
./install.sh
```

Replacing the folder is not enough for a clean update. Use `Repair Setup` in the app, or run `./install.sh` manually if the app cannot open, so the local Python environment, app signing, quarantine cleanup, and Safari registration are refreshed.

## Quick Fixes

`Repair Setup` is always available in the `Readiness` panel. If repair fails, click `Open Logs` in the same panel to inspect setup output.

Terminal fallback:

```bash
./install.sh
```

If the Safari extension disappears after Safari restarts, repeat the unsigned or temporary extension steps above.

If macOS says the app is damaged, make sure the `SWinyDL` folder was copied out of the DMG, then run:

```bash
./install.sh
```

If course discovery fails, export a debug log from the Safari popup and use the latest release before troubleshooting older extension behavior.
