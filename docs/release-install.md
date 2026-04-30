# SWinyDL Runtime Install

This folder came from the SWinyDL GitHub release DMG.

It contains only the runtime install:
- `SWinyDLSafariApp.app`
- `install.sh`
- the Python backend runtime package
- prebuilt CoreML runner binaries in `bin/`
- model/runtime assets
- `WebExtension`, used only for Safari's temporary-extension fallback
- this install guide and license notices

Build instructions and source-build files live on GitHub:
https://github.com/david00769/swinydl

This runtime DMG does not include the Safari Xcode project, Swift package source, source-build scripts, test suite, or developer docs.

## Install

1. Drag this `SWinyDL` folder out of the DMG.
2. Put it somewhere you want to keep it, such as `Documents` or `Applications`.
3. Do not run the installer from inside the mounted DMG.
4. Open Terminal.
5. Type `cd ` and drag this copied `SWinyDL` folder into Terminal.
6. Press `Enter`.
7. Run:

```bash
./install.sh
```

If Homebrew, `uv`, or `ffmpeg` are missing, approve the installer prompts.

The normal release install does not require Xcode, xcodegen, Swift, source code, or local compilation.

## Enable Safari

After the installer finishes:

1. Open Safari `Settings > Advanced`.
2. Turn on `Show features for web developers`.
3. Open Safari `Settings > Developer`.
4. Turn on `Allow unsigned extensions` and enter your Mac password when prompted.
5. Open Safari `Settings > Extensions`.
6. Enable `SWinyDL Safari`.
7. Open your Canvas or Echo360 page in Safari.
8. Open the `SWinyDL Safari` extension and start a job.

Safari resets `Allow unsigned extensions` when Safari quits, so repeat the Developer and Extensions steps after each Safari restart while SWinyDL is unsigned.

Do not double-click `SWinyDLSafariExtension.appex`. Safari discovers the extension through `SWinyDLSafariApp.app`.

## If The Extension Does Not Appear

1. Run `./install.sh` again from this copied folder.
2. Reopen `SWinyDLSafariApp.app`.
3. Confirm Safari `Settings > Developer > Allow unsigned extensions` is on.
4. Go back to Safari `Settings > Extensions` and enable `SWinyDL Safari`.

Temporary fallback:

1. Open Safari `Settings > Developer`.
2. Click `Add Temporary Extension...`.
3. Select the `WebExtension` folder in this copied `SWinyDL` folder.

Safari removes temporary extensions after 24 hours or when Safari quits, so repeat that step after each Safari restart if you use the fallback.

## Update

1. Download the newer SWinyDL DMG from GitHub Releases.
2. Quit SWinyDL.
3. Drag the new `SWinyDL` folder out of the DMG.
4. Replace the older copied `SWinyDL` folder.
5. Run `./install.sh` from the new copied folder.
