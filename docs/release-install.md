# SWinyDL Runtime Install

This folder came from the SWinyDL GitHub release DMG.

It contains only the runtime install:
- `SWinyDLSafariApp.app`
- `install.sh`
- the Python backend runtime package
- prebuilt CoreML runner binaries in `bin/`
- model/runtime assets
- `WebExtension`, used only for Safari's temporary-extension fallback
- `SWinyDL-WebExtension.zip`, the same temporary-extension files packaged as a selectable zip
- `USER-GUIDE.md`, the normal-user click-by-click guide
- this install guide and license notices

Build instructions and source-build files live on GitHub:
https://github.com/david00769/swinydl

Full user guide in this folder:
`USER-GUIDE.md`

Online user guide:
https://github.com/david00769/swinydl/blob/master/docs/user-guide.md

This runtime DMG does not include the Safari Xcode project, Swift package source, source-build scripts, test suite, or developer docs.

## Install

First download checklist:

1. Drag this `SWinyDL` folder out of the DMG.
2. Put it somewhere you want to keep it, such as `Documents` or `Applications`.
3. Do not run anything from inside the mounted DMG.
4. Control-click `SWinyDLSafariApp.app`, choose `Open`, then confirm the unsigned-app warning.
5. Click `Repair Setup` in the app's `Readiness` panel if setup, Safari registration, or model checks need repair.
6. If macOS asks whether `SWinyDLSafariApp` can access data from other apps, click `Allow`. That lets the Safari extension and app share queued jobs.

Terminal fallback:

Use this if macOS will not open the unsigned app, or if `Repair Setup` reports missing Homebrew, `uv`, or `ffmpeg`.

1. Open Terminal.
2. Type `cd ` and drag this copied `SWinyDL` folder into Terminal.
3. Press `Enter`.
4. Run:

```bash
./install.sh
```

The release DMG should already make `install.sh` executable. If Terminal says `permission denied`, make the installer executable and run it again:

```bash
chmod +x install.sh
./install.sh
```

If Homebrew, `uv`, or `ffmpeg` are missing, approve the installer prompts.

If signing fails with `resource fork, Finder information, or similar detritus not allowed`, download the latest release and run `./install.sh` again. Current installers scrub that metadata before signing.

If macOS blocks the unsigned app after setup, Control-click `SWinyDLSafariApp.app`, choose `Open`, then confirm the warning. Do not open the app from inside the mounted DMG.

The normal release install does not require Xcode, xcodegen, Swift, source code, or local compilation.

Signing and notarization are the future fix for removing the remaining Control-click or Terminal fallback.

## Enable Safari

After the installer finishes:

1. Open Safari `Settings > Advanced`.
2. Turn on `Show features for web developers`.
3. Open Safari `Settings > Developer`.
4. Turn on `Allow unsigned extensions` and enter your Mac password when prompted.
5. Open Safari `Settings > Extensions`.
6. Enable `SWinyDL Safari`.
7. Open your Canvas or Echo360 page in Safari.
8. Open the `SWinyDL Safari` extension.
9. Use `Open App` in the extension popup if you need to bring the full SWinyDL app window forward.
10. Start a job.

The full app entry point is either the popup's `Open App` button or `SWinyDLSafariApp.app` inside this copied `SWinyDL` folder.

`Repair Setup` is always available in the app's `Readiness` panel. It runs the non-interactive installer repair path, refreshes model checks, repairs local signing, and re-registers the Safari extension. If repair fails, click `Open Logs` in the same panel to inspect setup output.

The Readiness panel also shows `Safari handoff`. If it needs attention, allow the macOS app-data prompt when it appears so the extension can queue jobs into the native app.

If course discovery fails, click `Export Debug Log` in the Safari extension popup. It saves one sanitized JSON file with page/discovery state and excludes cookies, storage values, hidden input values, and full raw HTML.

## First Transcript

1. Open `SWinyDLSafariApp.app` from this copied `SWinyDL` folder.
2. Open a logged-in Canvas or EchoVideo lecture page in Safari.
3. Open the `SWinyDL Safari` extension popup.
4. Click `Reload` if needed.
5. Use `Check All` or `Uncheck All`, then choose the lessons you want.
6. Leave `Delete downloaded media after transcription` on unless you want to keep media files.
7. Click `Transcribe`, or click `Download + Transcribe` if you want the media retained during the run.
8. The popup shows `Queued for transcription. Progress appears in SWinyDL.`
9. If the app does not appear, the popup says `Queued, but SWinyDL did not open. Click Open App.`
10. Use the app window to watch progress and open finished `.txt` transcripts.

The default output folder is `swinydl-output` inside this copied `SWinyDL` folder. To choose a different transcript folder, use `Defaults > Output folder > Choose` in the native app. SWinyDL saves that folder for future Safari-launched jobs, and the `Open Outputs` row shows and opens the saved folder.

Temporary downloads, converted audio, and cookie handoff files use the `temp` folder inside the same copied `SWinyDL` folder.

Safari resets `Allow unsigned extensions` when Safari quits, so repeat the Developer and Extensions steps after each Safari restart while SWinyDL is unsigned.

Do not double-click `SWinyDLSafariExtension.appex`. Safari discovers the extension through `SWinyDLSafariApp.app`.

## If The Extension Does Not Appear

1. Open `SWinyDLSafariApp.app` and click `Repair Setup` in the `Readiness` panel.
2. Reopen `SWinyDLSafariApp.app` if Safari still does not list the extension.
3. Confirm Safari `Settings > Developer > Allow unsigned extensions` is on.
4. Go back to Safari `Settings > Extensions` and enable `SWinyDL Safari`.

Temporary fallback:

1. Open Safari `Settings > Developer`.
2. Click `Add Temporary Extension...`.
3. In the file picker, go to this copied `SWinyDL` folder.
4. Select the `WebExtension` folder, but do not open it.
5. Click `Select`.

If Safari will not let you select that folder, select `SWinyDL-WebExtension.zip` from the same copied `SWinyDL` folder instead.

Do not select `SWinyDLSafariApp.app`, `SWinyDLSafariExtension.appex`, or `manifest.json`. Safari wants the folder or zip file that contains `manifest.json`.

Safari removes temporary extensions after 24 hours or when Safari quits, so repeat that step after each Safari restart if you use the fallback.

If you installed an older temporary extension and EchoVideo still says the page is unsupported, remove the old temporary extension from Safari `Settings > Extensions`, then add the current `SWinyDL-WebExtension.zip` or `WebExtension` folder again. The current extension needs permission for `echo360.net.au`, which older temporary installs did not request.

## Update

1. Download the newer SWinyDL DMG from GitHub Releases.
2. Quit SWinyDL.
3. Drag the new `SWinyDL` folder out of the DMG.
4. Replace the older copied `SWinyDL` folder.
5. Open `SWinyDLSafariApp.app` from the new copied folder.
6. Click `Repair Setup` in the `Readiness` panel if setup or models need repair.
7. If the app cannot open, run `./install.sh` from the new copied folder.
