# SWinyDL

This folder came from the SWinyDL release DMG. It contains everything needed to run SWinyDL on a Mac with Apple Silicon. It does not need Xcode, Swift or any local compilation.

For step-by-step instructions, open `USER-GUIDE.md` in this folder. It is also online at https://github.com/david00769/swinydl/blob/master/docs/user-guide.md

## What Is In This Folder

- `SWinyDLSafariApp.app`: the Mac app. It contains the Safari extension.
- `install.sh`: setup and repair.
- `swinydl/`, `pyproject.toml` and `uv.lock`: the Python backend.
- `bin/`: prebuilt transcription and speaker-separation programs.
- `vendor/`: where setup puts the speech models.
- `WebExtension/` and `SWinyDL-WebExtension.zip`: only for Safari's temporary-extension fallback.
- `USER-GUIDE.md`, this file, `LICENSE` and `THIRD_PARTY_NOTICES.md`.

## Install

1. Drag this `SWinyDL` folder out of the DMG to a place you will keep it, such as `Documents`. Do not run anything from inside the mounted DMG.
2. Open Terminal, type `cd ` (with a trailing space), drag the copied `SWinyDL` folder into Terminal, and press `Enter`.
3. Run:

```bash
./install.sh
```

4. Approve the prompts if Homebrew, `uv` or `ffmpeg` are missing.

If Terminal says `permission denied`, run `chmod +x install.sh`, then `./install.sh` again.

The installer sets up Python, downloads the speech models, signs the app for this Mac, registers the Safari extension, and opens the app and Safari.

## Then

1. In Safari, open `Settings > Advanced` and turn on `Show features for web developers`.
2. Open `Settings > Developer` and turn on `Allow unsigned extensions`.
3. Open `Settings > Extensions` and enable `SWinyDL Safari`.
4. In the SWinyDL app, choose an output folder. If macOS asks whether SWinyDL can access data from other apps, click `Allow`.
5. Open a Canvas or Echo360 course page in Safari, click the `SWinyDL Safari` toolbar button, pick lessons and click `Transcribe`.

Safari turns `Allow unsigned extensions` off whenever it quits. Repeat steps 2 and 3 after each restart.

If macOS will not open the app, Control-click or right-click `SWinyDLSafariApp.app`, choose `Open`, and confirm. If it still will not open or says the app is damaged, run `./install.sh` again.

If something needs repair, click `Copy Repair Command` in the app, paste it into Terminal and press `Enter`. `USER-GUIDE.md` covers the other fixes.

## Update

1. Download the newer DMG, or use `Check for Updates` in the app.
2. Quit SWinyDL.
3. Replace this folder with the new `SWinyDL` folder from the DMG.
4. Run `./install.sh` from Terminal in the new folder.

Source code and build instructions: https://github.com/david00769/swinydl
