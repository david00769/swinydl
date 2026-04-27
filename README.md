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
- Xcode command line tools
- Homebrew
- `uv`, `ffmpeg`, and `xcodegen`

If you have never set this up before, run:

```bash
xcode-select --install
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install uv ffmpeg xcodegen
```

## Easiest Install

For most people, the best path is:

1. Download the current zip from [GitHub](https://github.com/david00769/swinydl/archive/refs/heads/codex/swinydl-initial-publish.zip)
2. Unzip it in Finder
3. Open Terminal
4. Type `cd ` and drag the unzipped SWinyDL folder into the Terminal window
5. Press `Enter`
6. If you have not installed Homebrew and the required tools yet, run the commands in `Before You Start`
7. Run:

```bash
./install.sh
```

`./install.sh` does the setup for you:
- creates the Python environment
- downloads the required local speech models if they are missing
- builds the Mac app and Safari extension wrapper
- opens the app and Safari when setup is finished

You do not need to download the Parakeet model manually.

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

1. Download the current zip from [GitHub](https://github.com/david00769/swinydl/archive/refs/heads/codex/swinydl-initial-publish.zip)
2. Unzip it
3. Open Terminal in the new folder
4. Run:

```bash
./install.sh
```

After the first GitHub Release is published, the Mac app can also check releases and tell you when a newer version exists.

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
