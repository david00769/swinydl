# SWinyDL

I coded this up in one weekend to help my daughter get transcripts from her lectures she can upload to NotebookLM.

SWinyDL downloads and transcribes Echo360 lecture recordings on Apple Silicon Macs. Transcription and speaker separation run locally with CoreML models. Nothing is sent to a hosted speech service.

It is built for lecture-style recordings: one main speaker and occasional audience questions.

## What It Does

- You open a Canvas or Echo360 course page in Safari.
- The SWinyDL Safari extension lists the lessons. You pick the ones you want.
- The SWinyDL Mac app downloads each lesson, transcribes it with speaker labels, and shows progress.
- You open the finished transcripts from the app.

For each lesson you get:

- `.txt`, the main transcript for reading
- `.srt`, timed captions
- `.json`, structured transcript data

## Requirements

- A Mac with Apple Silicon
- Safari
- Internet access during setup and while lessons download
- Homebrew, `uv` and `ffmpeg`. You do not need to install these first: `./install.sh` offers to install whichever are missing.

The normal install from the DMG does not need Xcode, Apple's command line tools, Swift or any local compilation. The DMG includes a prebuilt app and prebuilt transcription helper programs.

The app is unsigned. macOS and Safari ask you to confirm a few things the first time; the steps below cover each one.

## Install

1. Download the latest `SWinyDL-v...dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases).
2. Open the DMG.
3. Drag the `SWinyDL` folder out of the DMG to a place you will keep it, such as `Documents`. Do not run anything from inside the mounted DMG.
4. Open Terminal, type `cd ` (with a trailing space), drag the copied `SWinyDL` folder into the Terminal window, and press `Enter`.
5. Run:

```bash
./install.sh
```

Approve the prompts if Homebrew, `uv` or `ffmpeg` are missing.

`install.sh` then:

- checks that the folder has all the runtime files
- runs `uv sync` to create the Python environment
- downloads the speech models into the folder's `vendor/` directory if they are missing
- clears download quarantine from the app, ad-hoc signs it and verifies the signature
- registers the app and its Safari extension with macOS
- runs `swinydl doctor`
- opens the app and Safari

If Terminal says `permission denied`, run `chmod +x install.sh` and then `./install.sh` again.

Run `./install.sh --help` to see its options (`--repair`, `--non-interactive`, `--skip-open`, `--build-from-source`).

## First Run

### Enable the Safari extension

1. In Safari, open `Settings > Advanced` and turn on `Show features for web developers`.
2. Open `Settings > Developer` and turn on `Allow unsigned extensions`. macOS asks for your password.
3. Open `Settings > Extensions` and enable `SWinyDL Safari`.

Safari turns `Allow unsigned extensions` off every time it quits. Repeat steps 2 and 3 after each Safari restart.

### Set up the app

1. Open `SWinyDLSafariApp.app` from the copied `SWinyDL` folder. If macOS blocks it, Control-click or right-click the app, choose `Open`, and confirm. You can also select it and use Finder `File > Open`.
2. Choose an output folder. Queued jobs wait until one is set.
3. If macOS asks whether `SWinyDLSafariApp` can access data from other apps, click `Allow`. This lets the Safari extension hand jobs to the app.

The app's `Readiness` panel shows whether the Safari handoff, the Parakeet ASR model, the speaker diarizer and the output folder are ready.

### Transcribe lessons

1. In Safari, sign in and open a Canvas or Echo360 page that lists lectures.
2. Click the `SWinyDL Safari` toolbar button. Click `Reload` if the list looks stale.
3. Choose lessons, or use `Check All` and `Uncheck All`.
4. Click `Transcribe` for transcripts only.
5. To keep the lesson media as well, turn off `Delete downloaded media after transcription` and click `Download + Transcribe`. With the checkbox on, the media is deleted after transcription either way.
6. The popup shows `Queued for transcription.` If the app did not open, the popup says `Queued, but SWinyDL did not open.` Click `Open App`.
7. Watch progress in the app. Open finished transcripts from the job card.

For a click-by-click walkthrough, see the [user guide](docs/user-guide.md).

## Where Files Go

Transcripts go to the output folder you chose in the app. You can change it under `Defaults > Output folder` with `Choose`, `Open` and `Reset`.

Jobs started from Safari keep their temporary downloads, converted audio, job files and logs in the app's shared app-group container, not in your output folder. SWinyDL deletes each lesson's temporary media after transcription unless you asked to keep it.

## Updating

1. In the app, choose `Check for Updates`.
2. If a newer release exists, click `Download DMG`. SWinyDL saves it to Downloads and opens it.
3. Quit SWinyDL.
4. Drag the new `SWinyDL` folder out of the DMG and replace the old copied folder.
5. Run `./install.sh` from Terminal in the new folder. Replacing the folder alone is not enough: the installer refreshes the Python environment, signing, Safari registration and models.

You can also download the latest DMG yourself from [GitHub Releases](https://github.com/david00769/swinydl/releases).

## Troubleshooting

The app's `Diagnostics` panel has three tools:

- `Copy Repair Command` copies a Terminal command that runs `./install.sh` from your copied folder. The app cannot run the installer itself because it is sandboxed. Paste the command into Terminal and press `Enter`.
- `Copy Log Path` copies the path of the logs folder.
- `Export Diagnostics` saves a diagnostics zip. Cookies in job files are redacted.

To check the runtime from Terminal, run this in the copied folder:

```bash
uv run swinydl doctor
```

### The Safari extension does not appear

1. Check that `Allow unsigned extensions` is on in Safari `Settings > Developer`. Safari turns it off when it quits.
2. Quit and reopen `SWinyDLSafariApp.app` from the copied folder. Safari finds the extension through the app.
3. Run `./install.sh` again. It re-registers the app and extension with macOS.
4. If it still does not appear, add it as a temporary extension: in Safari `Settings > Developer`, click `Add Temporary Extension...`, go to the copied `SWinyDL` folder, select the `WebExtension` folder without opening it, and click `Select`. If the picker will not select the folder, select `SWinyDL-WebExtension.zip` instead.

Safari removes temporary extensions after 24 hours or when it quits, so repeat that step after each restart.

Do not double-click `SWinyDLSafariExtension.appex`, and do not select the app, the `.appex` or `manifest.json` as a temporary extension.

If an older temporary extension says an EchoVideo page is unsupported, remove it in Safari `Settings > Extensions` and add the current `WebExtension` folder or zip again. The current extension needs permission for `echo360.net.au`, which older copies did not request.

### A course page does not load

Click `Export Debug Log` in the extension popup. It saves one JSON file named like `swinydl-debug-YYYYMMDD-HHMMSS.json` in the app-group `DebugExports` folder. It contains page and lesson-discovery details. It leaves out cookies, stored page values, hidden form values and the full page HTML. Share that file when you report the problem.

### macOS will not open the app, or says it is damaged

Make sure you copied the `SWinyDL` folder out of the DMG. Then run `./install.sh` from the copied folder. It clears quarantine, re-signs the app and opens it.

### The installer says runtime files are missing

If `./install.sh` says the folder is missing runtime files, or `uv` reports `No module named 'swinydl'`, the copy is incomplete. Delete the copied `SWinyDL` folder, download the latest DMG and copy the folder out again.

### Terminal says `Operation not permitted`

If the error mentions a path like `Library/Containers/.../Data/Desktop/SWinyDL/install.sh`, the command is using a sandboxed path. Open Terminal yourself, type `cd `, drag the real copied `SWinyDL` folder from Finder into Terminal, press `Enter`, and run `./install.sh`.

### Signing fails with "resource fork, Finder information, or similar detritus"

Current installers remove that metadata before signing, so download the latest release and run `./install.sh` again. For an older copied folder, this also works:

```bash
/usr/bin/dot_clean -m SWinyDLSafariApp.app
/usr/bin/xattr -cr SWinyDLSafariApp.app
./install.sh
```

### The app says models are missing

Click `Copy Repair Command` and run it in Terminal, or run this in the copied folder:

```bash
uv run swinydl bootstrap-models
```

### A run looks slow

Long lectures can stay in one stage for a while during transcription or speaker separation. The app shows the current stage, elapsed time and recent activity.

## Command Line

The `swinydl` command line tool is included in the DMG folder and in a source checkout. Run it from that folder after `./install.sh`, with `uv run`:

```bash
uv run swinydl --help
```

The course commands `inspect`, `process` and `download` need your Echo360 login cookies. Give exactly one cookie source:

- `--cookies-from-browser safari` (or `chrome`, `chromium`, `firefox`, `edge`, `brave`) reads that browser's cookie store. Log in to the course in that browser first. Reading Safari's cookies needs Full Disk Access for your terminal app. Chrome asks for Keychain access.
- `--cookies FILE` reads a Netscape-format `cookies.txt` export.

SWinyDL keeps only the cookies for the course URL's host and its parent domains.

```bash
uv run swinydl inspect COURSE_URL --cookies-from-browser safari
uv run swinydl process COURSE_URL --cookies-from-browser safari
uv run swinydl download COURSE_URL --cookies cookies.txt --media audio
```

Other commands:

```bash
uv run swinydl process-manifest /path/to/job.json   # what the Mac app runs; the job file carries its own cookies
uv run swinydl transcribe /path/to/lecture.mp4      # a local file; no cookies needed
uv run swinydl bootstrap-models                     # download the speech models
uv run swinydl doctor                               # check the runtime
```

From the command line, output goes to `swinydl-output/` in the current folder unless you pass `--output`.

See [docs/index.md](docs/index.md) for the full command reference, how the pipeline works, model sources and building from source.

## More Detail

- [User guide](docs/user-guide.md): click-by-click steps for the Safari app
- [Technical overview](docs/index.md): commands, pipeline, models, building from source and releases
- [Third-party notices](THIRD_PARTY_NOTICES.md)
