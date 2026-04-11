from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from swinydl.models import TranscriptSegment, TranscriptWord, TranscribeOptions
from swinydl.workflow import transcribe_file


class LocalMediaEndToEndTests(unittest.TestCase):
    def test_transcribe_local_srt_writes_expected_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "lecture.srt"
            source.write_text(
                "\n".join(
                    [
                        "1",
                        "00:00:00,000 --> 00:00:01,200",
                        "Welcome everyone.",
                        "",
                        "2",
                        "00:00:01,500 --> 00:00:03,000",
                        "Let's begin.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = transcribe_file(source, TranscribeOptions(output_root=temp_path / "out"))

            self.assertEqual(result.status, "success")
            self.assertEqual(result.transcript_source, "native")
            self.assertFalse(result.diarized)
            self.assertTrue(result.artifacts.txt_path.exists())
            self.assertTrue(result.artifacts.srt_path.exists())
            self.assertTrue(result.artifacts.json_path.exists())

            txt_output = result.artifacts.txt_path.read_text(encoding="utf-8")
            self.assertEqual(txt_output.strip(), "Welcome everyone.\nLet's begin.")

            srt_output = result.artifacts.srt_path.read_text(encoding="utf-8")
            self.assertIn("Welcome everyone.", srt_output)
            self.assertIn("Let's begin.", srt_output)

            payload = json.loads(result.artifacts.json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "success")
            self.assertEqual(payload["transcript_source"], "native")
            self.assertIn("artifacts", payload)
            self.assertIn("segments", payload)
            self.assertIn("lesson", payload)
            self.assertEqual(len(payload["segments"]), 2)

    def test_transcribe_local_audio_writes_speaker_aware_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "lecture.wav"
            source.write_bytes(b"placeholder-audio")

            def fake_normalize(_source: Path, destination: Path) -> Path:
                destination.write_bytes(b"normalized-audio")
                return destination

            with patch("swinydl.workflow.normalize_media_to_wav", side_effect=fake_normalize), patch(
                "swinydl.workflow.transcribe_audio",
                return_value=(
                    [
                        TranscriptSegment(start=0.0, end=2.0, text="Welcome back to class.", speaker="LECTURER"),
                        TranscriptSegment(start=2.0, end=3.2, text="Could you repeat that?", speaker="AUDIENCE"),
                    ],
                    [
                        TranscriptWord(start=0.0, end=0.8, word="Welcome", speaker="LECTURER"),
                        TranscriptWord(start=0.8, end=1.2, word="back", speaker="LECTURER"),
                        TranscriptWord(start=1.2, end=2.0, word="to class.", speaker="LECTURER"),
                        TranscriptWord(start=2.0, end=2.6, word="Could", speaker="AUDIENCE"),
                        TranscriptWord(start=2.6, end=3.2, word="you repeat that?", speaker="AUDIENCE"),
                    ],
                    "en",
                    True,
                    "parakeet",
                    "parakeet-tdt-0.6b-v3-coreml",
                ),
            ):
                result = transcribe_file(
                    source,
                    TranscribeOptions(output_root=temp_path / "out", keep_audio=True),
                )

            self.assertEqual(result.status, "success")
            self.assertEqual(result.transcript_source, "asr")
            self.assertEqual(result.asr_backend, "parakeet")
            self.assertTrue(result.diarized)
            self.assertIsNotNone(result.artifacts.audio_path)
            self.assertTrue(result.artifacts.audio_path.exists())
            self.assertTrue(result.artifacts.txt_path.exists())
            self.assertTrue(result.artifacts.srt_path.exists())
            self.assertTrue(result.artifacts.json_path.exists())

            txt_output = result.artifacts.txt_path.read_text(encoding="utf-8")
            self.assertIn("Welcome back to class.", txt_output)
            self.assertIn("Could you repeat that?", txt_output)

            srt_output = result.artifacts.srt_path.read_text(encoding="utf-8")
            self.assertIn("[LECTURER] Welcome back to class.", srt_output)
            self.assertIn("[AUDIENCE] Could you repeat that?", srt_output)

            payload = json.loads(result.artifacts.json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "success")
            self.assertTrue(payload["diarized"])
            self.assertEqual(payload["asr_backend"], "parakeet")
            self.assertEqual(payload["model_name"], "parakeet-tdt-0.6b-v3-coreml")
            self.assertEqual(payload["segments"][0]["speaker"], "LECTURER")
            self.assertEqual(payload["segments"][1]["speaker"], "AUDIENCE")
