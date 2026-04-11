# SWinyDL v4

See the repository root [README](../README.md) for the supported install and usage flow.

The v4 line is transcript-first:

- `swinydl inspect COURSE_URL`
- `swinydl process COURSE_URL`
- `swinydl download COURSE_URL --media audio|video|both`
- `swinydl transcribe PATH`
- `swinydl doctor`

`swinydl download` remains the command for explicitly retrieving Echo360 media artifacts. `swinydl process` is the normal end-to-end transcript workflow.

For day-to-day use, the simplest entrypoint is:

```bash
uv run app.py
```

With no arguments, that launcher opens Chrome with the persistent profile, waits for you to log in and navigate to the target Canvas or Echo360 page, captures the current browser URL when you press Enter again, and then runs the normal `swinydl process` workflow against that captured URL.

Supported scope:

- macOS Apple Silicon
- Chrome or Chromium
- Python `>=3.11`
- Swift toolchain available on `PATH`
- package install via `pip` or `uv`

The old video-downloader implementation, PhantomJS, Firefox, and custom HLS code are intentionally removed from the supported path.

Dependency ranges live in `pyproject.toml`, the tested resolution lives in `uv.lock`, and `swinydl doctor` is only for runtime readiness checks.

There is no separate `requirements.txt` or `MANIFEST.in` workflow in v4.

The transcription stack now uses:

- local Parakeet CoreML via the repo-local Swift runner
- local CoreML speaker diarization via a second Swift runner

`--asr-backend auto` resolves to Parakeet CoreML.

The flow is:

1. Python normalizes media to mono 16 kHz WAV.
2. Python invokes the local Swift runner.
3. Swift loads the staged CoreML Parakeet bundles and runs transcription on Apple Silicon.
4. Swift returns token timings as JSON.
5. Python reconstructs words and transcript segments, then writes `.txt`, `.srt`, and `.json`.

Speaker diarization is on by default and runs through the local CoreML diarizer bundles staged under `vendor/speaker-diarization-coreml` or pointed to by `ECHO360_DIARIZER_COREML_DIR`.

The supported staging path is:

```bash
swinydl bootstrap-models
```

That command downloads the repo-local CoreML bundles from the public Hugging Face sources documented below.

## Model Provenance

The repo runs staged local CoreML bundles, but the update sources are public:

- ASR CoreML pull source: [FluidInference/parakeet-tdt-0.6b-v3-coreml](https://huggingface.co/FluidInference/parakeet-tdt-0.6b-v3-coreml)
- ASR canonical base model: [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- Diarizer CoreML pull source: [FluidInference/speaker-diarization-coreml](https://huggingface.co/FluidInference/speaker-diarization-coreml)
- Diarizer canonical base pipeline: [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

The diarizer bundle corresponds conceptually to:

- segmentation via [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
- speaker embeddings via [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM)
- VBx-style clustering parameters carried by the `community-1` pipeline sidecars

When refreshing models, prefer the CoreML repos for direct staging updates and use the canonical upstream model cards to evaluate architecture or license changes.

The exact staging instructions now live in the root [README](../README.md) and use the built-in `swinydl bootstrap-models` command.
