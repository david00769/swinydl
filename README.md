# SWinyDL

I coded this up in one weekend to help my daughter get transcripts from her lectures she can upload to NotebookLLM

SWinyDL downloads and transcribes Echo360 lecture recordings on Apple Silicon Macs.

It is designed for:
- macOS on Apple Silicon
- Safari as the main browser flow
- lecture-style content with one main speaker and occasional audience questions

Tested on:
- macOS 26.4 (`25E246`) on Apple Silicon

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
- opens the app and Safari when setup is finished

For the normal DMG install, `./install.sh` is still required. It prepares the local Python environment, checks `ffmpeg`, verifies the app can run, and opens Safari so you can enable the extension.

You do not need to download the Parakeet model manually.

## Developer Install

If you want to build SWinyDL from source instead of using the DMG:

1. Download the source zip from [GitHub](https://github.com/david00769/swinydl/archive/refs/heads/master.zip)
2. Unzip it
3. Install Apple's command line tools if needed:

```bash
xcode-select --install
```

4. Run:

```bash
./install.sh --build-from-source
```

The source build path can install `xcodegen` and uses `xcodebuild` locally.

Xcode command line tools are only needed for this developer source-build path.

## First Run

After the installer finishes:

1. Open Safari `Settings > Extensions`
2. Enable `SWinyDL Safari`
3. If the extension does not appear, enable Safari's Develop menu and turn on `Allow Unsigned Extensions`
4. Open your Canvas or Echo360 page in Safari
5. Open the `SWinyDL Safari` extension
6. Choose the lessons you want
7. Start the job

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
2. Open Safari `Settings > Extensions`
3. If needed, enable Safari's Develop menu and turn on `Allow Unsigned Extensions`

You can also check app health in Terminal:

```bash
swinydl doctor
```

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

If you are comfortable with the command line, you can still:

```bash
swinydl process COURSE_URL
swinydl process-manifest /path/to/job.json
swinydl transcribe /path/to/local/file.mp4
```

The older Chrome-guided launcher still exists as a fallback:

```bash
uv run app.py
```

## More Detail

If you want the lower-level technical notes, commands, and model details, see:
- [docs/index.md](docs/index.md)
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
