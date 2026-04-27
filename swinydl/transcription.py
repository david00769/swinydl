from __future__ import annotations

"""Audio normalization, CoreML ASR execution, and speaker assignment helpers."""

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any
from contextlib import contextmanager
import fcntl
import os
import platform
import shutil
import subprocess

from .echo_exceptions import DependencyMissingError, TranscriptionError
from .models import TranscriptSegment, TranscriptWord
from .app_paths import cache_dir
from .system import configure_runtime_ssl, find_swift_binary

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
DEFAULT_PARAKEET_COREML_VERSION = "v3"
DEFAULT_PARAKEET_COREML_DIRNAME = "parakeet-tdt-0.6b-v3-coreml"
DEFAULT_DIARIZER_COREML_DIRNAME = "speaker-diarization-coreml"


@dataclass(frozen=True)
class SpeakerTurn:
    """A diarized speaker span returned by the local CoreML diarizer."""

    start: float
    end: float
    speaker: str


def normalize_media_to_wav(source: Path, destination: Path) -> Path:
    """Convert any supported media input into mono 16 kHz WAV for ASR."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise DependencyMissingError("ffmpeg is required to normalize audio for transcription.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    hwaccel_args = _ffmpeg_hwaccel_args(source)
    command = [
        ffmpeg,
        "-y",
        *hwaccel_args,
    ]
    command.extend(_ffmpeg_audio_normalize_args(source, destination))
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0 and hwaccel_args:
        retry_command = [ffmpeg, "-y", *_ffmpeg_audio_normalize_args(source, destination)]
        completed = subprocess.run(retry_command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise TranscriptionError(completed.stderr.strip() or "ffmpeg failed to normalize audio.")
    return destination


def transcribe_with_parakeet(audio_path: Path) -> tuple[list[TranscriptSegment], list[TranscriptWord], str | None, str]:
    """Run the local Parakeet CoreML backend and normalize its JSON output."""
    payload = _run_parakeet_coreml(audio_path)
    words = _words_from_token_timings(payload.get("tokenTimings") or [])
    duration = float(payload.get("duration") or 0.0)
    transcript_text = str(payload.get("text") or "").strip()
    segments = _segments_from_words(words) if words else []
    if not segments and transcript_text:
        segments = [TranscriptSegment(start=0.0, end=duration, text=transcript_text)]
    if not segments:
        raise TranscriptionError("Parakeet CoreML returned no transcript segments.")
    return segments, words, "en", str(payload.get("modelName") or DEFAULT_PARAKEET_COREML_DIRNAME)


def transcribe_audio(
    audio_path: Path,
    *,
    asr_backend: str,
    diarization_mode: str,
    progress_callback=None,
) -> tuple[list[TranscriptSegment], list[TranscriptWord], str | None, bool, str, str]:
    """Transcribe one normalized audio file and optionally label speaker turns."""
    resolved_backend = resolve_asr_backend(asr_backend)
    diarization_ready, reason = diarization_runtime_status(require_token=True)

    effective_diarization = False
    if diarization_mode == "on":
        if not diarization_ready:
            raise DependencyMissingError(reason or "Speaker diarization is not available in this runtime.")
        effective_diarization = True
    elif diarization_mode == "auto":
        effective_diarization = diarization_ready

    if progress_callback is not None:
        progress_callback("transcribing", "Running local Parakeet speech recognition.")
    if resolved_backend == "parakeet":
        segments, words, language, model_name = transcribe_with_parakeet(audio_path)
    else:  # pragma: no cover - resolve_asr_backend should prevent this
        raise DependencyMissingError(f"Unknown ASR backend: {resolved_backend}")

    if effective_diarization:
        if progress_callback is not None:
            progress_callback("diarizing", "Separating dominant speaker and audience turns.")
        segments, words = diarize_transcript(audio_path, segments, words)

    return segments, words, language, effective_diarization, resolved_backend, model_name


def resolve_asr_backend(requested: str) -> str:
    """Resolve a requested ASR backend name to a concrete local backend."""
    if requested == "parakeet":
        if not parakeet_backend_available():
            status = parakeet_backend_status()
            raise DependencyMissingError(str(status["reason"]))
        return "parakeet"
    if requested != "auto":
        raise DependencyMissingError(f"Unknown ASR backend: {requested}")
    if parakeet_backend_available():
        return "parakeet"
    status = parakeet_backend_status()
    raise DependencyMissingError(str(status["reason"]))


def parakeet_backend_available() -> bool:
    """Return whether the local Parakeet CoreML runner is ready to use."""
    return bool(parakeet_backend_status()["ready"])


def parakeet_backend_status() -> dict[str, object]:
    """Return a structured readiness check for the local Parakeet backend."""
    swift = find_swift_binary()
    model_dir = _parakeet_coreml_model_dir()
    if swift is None:
        return {
            "ready": False,
            "reason": "Swift is not installed. Install Xcode command line tools to build the Parakeet CoreML runner.",
            "model_dir": str(model_dir),
        }
    if not _parakeet_coreml_models_exist(model_dir):
        return {
            "ready": False,
            "reason": (
                f"Parakeet CoreML assets were not found at {model_dir}. "
                "Run `swinydl bootstrap-models --target parakeet` or set ECHO360_PARAKEET_COREML_DIR."
            ),
            "model_dir": str(model_dir),
        }
    package_dir = _parakeet_runner_package_dir()
    if not package_dir.exists():
        return {
            "ready": False,
            "reason": f"Swift runner package is missing at {package_dir}.",
            "model_dir": str(model_dir),
        }
    return {"ready": True, "reason": None, "model_dir": str(model_dir)}


def diarization_runtime_status(*, require_token: bool) -> tuple[bool, str | None]:
    """Return whether local speaker diarization is ready.

    The ``require_token`` parameter is retained for API compatibility with earlier
    Python-based diarization paths. The local CoreML diarizer does not need a token.
    """
    status = diarizer_backend_status()
    if not status["ready"]:
        return False, str(status["reason"])
    return True, None


def _ffmpeg_audio_normalize_args(source: Path, destination: Path) -> list[str]:
    """Return the ffmpeg arguments needed for transcript-friendly audio output."""
    return [
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(destination),
    ]


def _ffmpeg_hwaccel_args(source: Path) -> list[str]:
    """Use VideoToolbox decoding on Apple Silicon when the source is video."""
    if (
        platform.system() == "Darwin"
        and platform.machine() == "arm64"
        and source.suffix.lower() in VIDEO_EXTENSIONS
    ):
        return ["-hwaccel", "videotoolbox"]
    return []


def diarize_transcript(
    audio_path: Path,
    segments: list[TranscriptSegment],
    words: list[TranscriptWord],
) -> tuple[list[TranscriptSegment], list[TranscriptWord]]:
    """Assign speaker labels to ASR words and segments using local CoreML turns."""
    configure_runtime_ssl()
    turns = [
        SpeakerTurn(
            float(item.get("startTime", 0.0)),
            float(item.get("endTime", 0.0)),
            str(item.get("speakerId") or ""),
        )
        for item in (_run_diarizer_coreml(audio_path).get("segments") or [])
        if item.get("speakerId")
    ]
    if not turns:
        return segments, words

    diarized_words = [_assign_word_speaker(word, turns) for word in words]
    diarized_segments = [_assign_segment_speaker(segment, diarized_words, turns) for segment in segments]
    return diarized_segments, diarized_words


def _run_parakeet_coreml(audio_path: Path) -> dict[str, Any]:
    """Execute the Swift Parakeet runner and parse its JSON payload."""
    configure_runtime_ssl()
    with _coreml_runner_lock():
        runner = _ensure_parakeet_coreml_runner()
        model_dir = _parakeet_coreml_model_dir()
        version = os.environ.get("ECHO360_PARAKEET_COREML_VERSION", DEFAULT_PARAKEET_COREML_VERSION)
        completed = subprocess.run(
            [
                str(runner),
                "--audio",
                str(audio_path),
                "--model-dir",
                str(model_dir),
                "--version",
                version,
            ],
            capture_output=True,
            text=True,
        )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Parakeet CoreML runner failed."
        raise TranscriptionError(message)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise TranscriptionError("Parakeet CoreML runner returned invalid JSON.") from exc


def _ensure_parakeet_coreml_runner() -> Path:
    """Build or locate the Parakeet Swift executable."""
    status = parakeet_backend_status()
    if not status["ready"]:
        raise DependencyMissingError(str(status["reason"]))
    return _ensure_swift_runner("parakeet-coreml-runner")


def _run_diarizer_coreml(audio_path: Path) -> dict[str, Any]:
    """Execute the Swift speaker diarizer runner and parse its JSON payload."""
    configure_runtime_ssl()
    with _coreml_runner_lock():
        runner = _ensure_diarizer_coreml_runner()
        model_dir = _diarizer_coreml_model_dir()
        completed = subprocess.run(
            [
                str(runner),
                "--audio",
                str(audio_path),
                "--model-dir",
                str(model_dir),
            ],
            capture_output=True,
            text=True,
        )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Speaker diarizer CoreML runner failed."
        raise TranscriptionError(message)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise TranscriptionError("Speaker diarizer CoreML runner returned invalid JSON.") from exc


def _ensure_diarizer_coreml_runner() -> Path:
    """Build or locate the speaker diarizer Swift executable."""
    status = diarizer_backend_status()
    if not status["ready"]:
        raise DependencyMissingError(str(status["reason"]))
    return _ensure_swift_runner("speaker-diarizer-coreml-runner")


def _ensure_swift_runner(product_name: str) -> Path:
    """Build a Swift product on demand and return its release binary path."""
    package_dir = _parakeet_runner_package_dir()
    swift = find_swift_binary()
    if swift is None:
        raise DependencyMissingError("Swift is not installed.")
    bin_path = subprocess.run(
        [swift, "build", "--package-path", str(package_dir), "-c", "release", "--show-bin-path"],
        capture_output=True,
        text=True,
    )
    if bin_path.returncode == 0:
        runner = Path(bin_path.stdout.strip()) / product_name
        if runner.exists():
            return runner
    build = subprocess.run(
        [swift, "build", "--package-path", str(package_dir), "-c", "release", "--product", product_name],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        raise TranscriptionError(build.stderr.strip() or f"Failed to build the {product_name}.")
    bin_path = subprocess.run(
        [swift, "build", "--package-path", str(package_dir), "-c", "release", "--show-bin-path"],
        capture_output=True,
        text=True,
    )
    if bin_path.returncode != 0:
        raise TranscriptionError(bin_path.stderr.strip() or f"Failed to locate the {product_name}.")
    runner = Path(bin_path.stdout.strip()) / product_name
    if not runner.exists():
        raise TranscriptionError(f"{product_name} was not built at {runner}.")
    return runner


@contextmanager
def _coreml_runner_lock():
    """Serialize local CoreML runner access across processes.

    FluidAudio/CoreML initialization can fail intermittently when multiple
    wrapper jobs launch model runners at the same time. A coarse file lock is
    acceptable here because this app is transcript-first and reliability is
    more important than parallel inference throughput.
    """
    lock_dir = cache_dir() / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "coreml-runner.lock"
    with lock_path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _parakeet_runner_package_dir() -> Path:
    """Return the package directory that owns the Swift runner executables."""
    return Path(__file__).resolve().parents[1] / "swift" / "ParakeetCoreMLRunner"


def _parakeet_coreml_model_dir() -> Path:
    """Return the configured Parakeet model directory."""
    configured = os.environ.get("ECHO360_PARAKEET_COREML_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "vendor" / DEFAULT_PARAKEET_COREML_DIRNAME


def _parakeet_coreml_models_exist(directory: Path) -> bool:
    """Return whether a directory contains the staged Parakeet CoreML bundle."""
    required = (
        "Preprocessor.mlmodelc",
        "Encoder.mlmodelc",
        "Decoder.mlmodelc",
        "JointDecision.mlmodelc",
        "parakeet_vocab.json",
    )
    return directory.exists() and all((directory / name).exists() for name in required)


def diarizer_backend_status() -> dict[str, object]:
    """Return a structured readiness check for the local diarizer backend."""
    swift = find_swift_binary()
    model_dir = _diarizer_coreml_model_dir()
    if swift is None:
        return {
            "ready": False,
            "reason": "Swift is not installed. Install Xcode command line tools to build the speaker diarizer runner.",
            "model_dir": str(model_dir),
        }
    if not _diarizer_coreml_models_exist(model_dir):
        return {
            "ready": False,
            "reason": (
                f"Speaker diarizer CoreML assets were not found at {model_dir}. "
                "Run `swinydl bootstrap-models --target diarizer` or set ECHO360_DIARIZER_COREML_DIR."
            ),
            "model_dir": str(model_dir),
        }
    package_dir = _parakeet_runner_package_dir()
    if not package_dir.exists():
        return {
            "ready": False,
            "reason": f"Swift runner package is missing at {package_dir}.",
            "model_dir": str(model_dir),
        }
    return {"ready": True, "reason": None, "model_dir": str(model_dir)}


def diarizer_backend_available() -> bool:
    """Return whether the local CoreML diarizer is ready to use."""
    return bool(diarizer_backend_status()["ready"])


def _diarizer_coreml_model_dir() -> Path:
    """Return the configured local speaker diarizer model directory."""
    configured = os.environ.get("ECHO360_DIARIZER_COREML_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "vendor" / DEFAULT_DIARIZER_COREML_DIRNAME


def _diarizer_coreml_models_exist(directory: Path) -> bool:
    """Return whether a directory contains the staged offline diarizer bundle."""
    required = (
        "Segmentation.mlmodelc",
        "FBank.mlmodelc",
        "Embedding.mlmodelc",
        "PldaRho.mlmodelc",
        "plda-parameters.json",
    )
    return directory.exists() and all((directory / name).exists() for name in required)


def _words_from_token_timings(raw_timings: list[dict[str, Any]]) -> list[TranscriptWord]:
    """Collapse token timings into word timings using sentencepiece boundaries."""
    words: list[TranscriptWord] = []
    current_text = ""
    start = 0.0
    end = 0.0
    for item in raw_timings:
        token = str(item.get("token") or "")
        if not token or token in {"<blank>", "<pad>"}:
            continue
        token_start = float(item.get("startTime", 0.0))
        token_end = float(item.get("endTime", token_start))
        starts_new_word = _is_word_boundary_token(token) or not current_text
        if starts_new_word and current_text.strip():
            words.append(TranscriptWord(start=start, end=end, word=current_text.strip()))
            current_text = ""
        if starts_new_word:
            current_text = _strip_word_boundary_prefix(token)
            start = token_start
        else:
            current_text += token
        end = token_end
    if current_text.strip():
        words.append(TranscriptWord(start=start, end=end, word=current_text.strip()))
    return words


def _is_word_boundary_token(token: str) -> bool:
    """Return whether a token starts a new word in the Parakeet output."""
    return token.startswith("▁") or token.startswith(" ")


def _strip_word_boundary_prefix(token: str) -> str:
    """Remove the sentencepiece boundary marker from a token."""
    if _is_word_boundary_token(token):
        return token[1:]
    return token


def _segments_from_words(words: list[TranscriptWord]) -> list[TranscriptSegment]:
    """Group timed words into sentence-like transcript segments."""
    segments: list[TranscriptSegment] = []
    buffer: list[TranscriptWord] = []
    for word in words:
        buffer.append(word)
        gap = 0.0
        if len(buffer) > 1:
            gap = max(0.0, word.start - buffer[-2].end)
        if (
            word.word.endswith((".", "?", "!"))
            or gap > 1.0
            or len(buffer) >= 32
        ):
            segments.append(_segment_from_word_buffer(buffer))
            buffer = []
    if buffer:
        segments.append(_segment_from_word_buffer(buffer))
    return segments


def _segment_from_word_buffer(words: list[TranscriptWord]) -> TranscriptSegment:
    """Build one segment from a contiguous word buffer."""
    return TranscriptSegment(
        start=words[0].start,
        end=words[-1].end,
        text=_join_tokens([word.word for word in words]),
    )


def _join_tokens(tokens: list[str]) -> str:
    """Join tokenized words back into readable sentence text."""
    text = ""
    for token in tokens:
        if not text:
            text = token
        elif token[:1] in {".", ",", "!", "?", ";", ":"}:
            text += token
        else:
            text += f" {token}"
    return text.strip()


def _assign_word_speaker(word: TranscriptWord, turns: list[SpeakerTurn]) -> TranscriptWord:
    """Assign the best overlapping speaker label to a word."""
    speaker = _best_speaker(word.start, word.end, turns)
    return replace(word, speaker=speaker)


def _assign_segment_speaker(
    segment: TranscriptSegment,
    words: list[TranscriptWord],
    turns: list[SpeakerTurn],
) -> TranscriptSegment:
    """Assign the dominant speaker label to a transcript segment."""
    speaker_scores: dict[str, float] = {}
    for word in words:
        if word.speaker is None:
            continue
        overlap = _overlap_seconds(segment.start, segment.end, word.start, word.end)
        if overlap <= 0:
            continue
        speaker_scores[word.speaker] = speaker_scores.get(word.speaker, 0.0) + overlap
    speaker = max(speaker_scores, key=speaker_scores.get) if speaker_scores else _best_speaker(segment.start, segment.end, turns)
    return replace(segment, speaker=speaker)


def _best_speaker(start: float, end: float, turns: list[SpeakerTurn]) -> str | None:
    """Return the speaker turn with the highest overlap against a time span."""
    best_speaker = None
    best_overlap = 0.0
    for turn in turns:
        overlap = _overlap_seconds(start, end, turn.start, turn.end)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = turn.speaker
    return best_speaker


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    """Return the overlap in seconds between two time ranges."""
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
