from pathlib import Path
import unittest
from unittest.mock import patch

from swinydl.models import TranscriptSegment, TranscriptWord
from swinydl.transcription import (
    SpeakerTurn,
    _assign_segment_speaker,
    _assign_word_speaker,
    _ffmpeg_hwaccel_args,
    _words_from_token_timings,
    diarizer_backend_status,
    diarization_runtime_status,
    parakeet_backend_status,
    resolve_asr_backend,
    transcribe_audio,
)


class TranscriptionPlatformTests(unittest.TestCase):
    def test_ffmpeg_hwaccel_uses_videotoolbox_for_video_on_mac_silicon(self):
        with patch("swinydl.transcription.platform.system", return_value="Darwin"), patch(
            "swinydl.transcription.platform.machine", return_value="arm64"
        ):
            self.assertEqual(
                _ffmpeg_hwaccel_args(Path("lecture.mp4")),
                ["-hwaccel", "videotoolbox"],
            )

    def test_ffmpeg_hwaccel_skips_audio_inputs(self):
        with patch("swinydl.transcription.platform.system", return_value="Darwin"), patch(
            "swinydl.transcription.platform.machine", return_value="arm64"
        ):
            self.assertEqual(_ffmpeg_hwaccel_args(Path("lecture.m4a")), [])

    def test_resolve_asr_backend_auto_prefers_parakeet_when_available(self):
        with patch("swinydl.transcription.parakeet_backend_available", return_value=True):
            self.assertEqual(resolve_asr_backend("auto"), "parakeet")

    def test_parakeet_backend_status_requires_local_coreml_assets(self):
        with patch("swinydl.transcription.find_swift_binary", return_value="/usr/bin/swift"), patch(
            "swinydl.transcription._parakeet_coreml_models_exist", return_value=False
        ):
            status = parakeet_backend_status()
        self.assertFalse(status["ready"])
        self.assertIn("CoreML assets", status["reason"])

    def test_diarization_runtime_status_uses_local_coreml_backend(self):
        with patch("swinydl.transcription.find_swift_binary", return_value="/usr/bin/swift"), patch(
            "swinydl.transcription._diarizer_coreml_models_exist", return_value=True
        ):
            ready, reason = diarization_runtime_status(require_token=False)
        self.assertTrue(ready)
        self.assertIsNone(reason)

    def test_diarizer_backend_status_requires_local_coreml_assets(self):
        with patch("swinydl.transcription.find_swift_binary", return_value="/usr/bin/swift"), patch(
            "swinydl.transcription._diarizer_coreml_models_exist", return_value=False
        ):
            status = diarizer_backend_status()
        self.assertFalse(status["ready"])
        self.assertIn("CoreML assets", status["reason"])

    def test_word_and_segment_speaker_assignment_uses_overlap(self):
        turns = [
            SpeakerTurn(start=0.0, end=1.0, speaker="SPEAKER_00"),
            SpeakerTurn(start=1.0, end=2.0, speaker="SPEAKER_01"),
        ]
        word = TranscriptWord(start=1.1, end=1.4, word="hello")
        diarized_word = _assign_word_speaker(word, turns)
        diarized_segment = _assign_segment_speaker(
            TranscriptSegment(start=1.0, end=1.5, text="hello"),
            [diarized_word],
            turns,
        )
        self.assertEqual(diarized_word.speaker, "SPEAKER_01")
        self.assertEqual(diarized_segment.speaker, "SPEAKER_01")

    def test_words_from_token_timings_reconstruct_sentencepiece_words(self):
        words = _words_from_token_timings(
            [
                {"token": " hello", "startTime": 0.0, "endTime": 0.2},
                {"token": "world", "startTime": 0.2, "endTime": 0.4},
                {"token": "!", "startTime": 0.4, "endTime": 0.5},
                {"token": " again", "startTime": 0.6, "endTime": 0.8},
            ]
        )
        self.assertEqual([word.word for word in words], ["helloworld!", "again"])

    def test_transcribe_audio_uses_parakeet_backend_when_requested(self):
        with patch("swinydl.transcription.parakeet_backend_available", return_value=True), patch(
            "swinydl.transcription.transcribe_with_parakeet",
            return_value=(
                [TranscriptSegment(start=0.0, end=1.0, text="Hello from Parakeet")],
                [TranscriptWord(start=0.0, end=0.5, word="Hello")],
                "en",
                "parakeet-tdt-0.6b-v3-coreml",
            ),
        ), patch(
            "swinydl.transcription.diarization_runtime_status",
            return_value=(False, "not configured"),
        ):
            segments, words, language, diarized, backend, model_name = transcribe_audio(
                Path("lecture.wav"),
                asr_backend="parakeet",
                diarization_mode="auto",
            )
        self.assertEqual(language, "en")
        self.assertFalse(diarized)
        self.assertEqual(backend, "parakeet")
        self.assertEqual(model_name, "parakeet-tdt-0.6b-v3-coreml")
        self.assertEqual(segments[0].text, "Hello from Parakeet")
        self.assertEqual(words[0].word, "Hello")
