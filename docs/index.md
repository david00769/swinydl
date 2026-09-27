# SWinyDL

SWinyDL downloads and transcribes Echo360 lecture recordings on Apple Silicon Macs. Transcription and speaker separation run locally with CoreML models; nothing is sent to a hosted speech service.

It is built for lecture-style recordings: one main speaker and occasional audience questions.

**Latest version: 4.1.0.** [Download the DMG from GitHub Releases](https://github.com/david00769/swinydl/releases/latest).

## How It Works

1. Open a Canvas or Echo360 course page in Safari.
2. The SWinyDL Safari extension lists the lessons. Pick the ones you want.
3. The SWinyDL Mac app downloads each lesson, transcribes it with speaker labels, and shows progress.
4. Open the finished transcripts from the app.

For each lesson you get a `.txt` transcript for reading, `.srt` timed captions, and a `.json` file with the structured transcript.

## Requirements

- A Mac with Apple Silicon
- Safari
- Internet access during setup and while lessons download

The installer offers to install Homebrew, `uv` and `ffmpeg` if they are missing. The DMG includes a prebuilt app, so you do not need Xcode or any local compilation.

## Install

1. Download `SWinyDL-v4.1.0.dmg` from [GitHub Releases](https://github.com/david00769/swinydl/releases/latest) and open it.
2. Drag the `SWinyDL` folder out of the DMG to a place you will keep it, such as `Documents`.
3. In Terminal, go to that folder and run `./install.sh`.
4. In Safari, turn on `Settings > Developer > Allow unsigned extensions`, then enable `SWinyDL Safari` in `Settings > Extensions`. Safari turns unsigned extensions off each time it quits, so repeat this after a restart.
5. Open `SWinyDLSafariApp.app` and choose an output folder.

The [user guide](user-guide.md) walks through each step, first transcripts and quick fixes.

## What's New in 4.1.0

- **Fixed:** in 4.0.12 the app could not read job status, so queued jobs kept relaunching and never showed progress. Upgrading is recommended.
- **Fixed:** lesson-page video and caption links are found again, a finished transcript is kept if a later media download fails, and caption files (SRT and WebVTT) are read more reliably.
- **Safer:** the extension exports only the cookies the course page needs, lesson ids cannot write outside the output folder, and session cookies are no longer left in temporary files.
- **Changed:** the command line no longer drives Chrome. Course commands read your Echo360 login cookies from a browser (`--cookies-from-browser safari`) or a `cookies.txt` file (`--cookies`).

Full notes: [SWinyDL v4.1.0](https://github.com/david00769/swinydl/releases/tag/v4.1.0).

## Command Line

The Safari app is the main way to use SWinyDL. The same tool also runs from Terminal in the `SWinyDL` folder:

```bash
uv run swinydl process COURSE_URL --cookies-from-browser safari
uv run swinydl transcribe /path/to/lecture.mp4
uv run swinydl doctor
```

Log in to the course in Safari first. Reading Safari's cookies needs Full Disk Access for your terminal app. See the [technical overview](technical.md) for every command and option.

## More

- [User guide](user-guide.md): install, first run, transcripts and quick fixes
- [Technical overview](technical.md): how it works, the command line, speech models, building from source and releases
- [Source code and issues](https://github.com/david00769/swinydl)
