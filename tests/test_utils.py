import unittest
from unittest.mock import patch

from swinydl.models import LessonAsset, LessonManifest, ProcessOptions
from swinydl.utils import lesson_key
from swinydl.workflow import _resolve_transcript_source


class UtilityTests(unittest.TestCase):
    def test_lesson_key_uses_requested_shape(self):
        key = lesson_key("2026-04-01", "lesson-1", 3, "Week 1 / Intro")
        self.assertEqual(key, "2026-04-01__lesson-1__week-1-intro")

    def test_auto_source_prefers_native_when_present(self):
        lesson = LessonManifest(
            lesson_id="lesson-1",
            title="Lesson",
            date="2026-04-01",
            lesson_url="https://example.edu/lesson",
            index=1,
            assets=[LessonAsset(kind="caption", url="https://cdn.example/lesson.vtt", ext="vtt")],
        )
        options = ProcessOptions(output_root=__import__("pathlib").Path("swinydl-output"), diarization_mode="off")
        self.assertEqual(_resolve_transcript_source(options, lesson), "native")

    def test_diarization_on_forces_asr_even_with_native_caption(self):
        lesson = LessonManifest(
            lesson_id="lesson-1",
            title="Lesson",
            date="2026-04-01",
            lesson_url="https://example.edu/lesson",
            index=1,
            assets=[LessonAsset(kind="caption", url="https://cdn.example/lesson.vtt", ext="vtt")],
        )
        options = ProcessOptions(output_root=__import__("pathlib").Path("swinydl-output"), diarization_mode="on")
        self.assertEqual(_resolve_transcript_source(options, lesson), "asr")

    def test_diarization_auto_prefers_asr_when_runtime_ready(self):
        lesson = LessonManifest(
            lesson_id="lesson-1",
            title="Lesson",
            date="2026-04-01",
            lesson_url="https://example.edu/lesson",
            index=1,
            assets=[LessonAsset(kind="caption", url="https://cdn.example/lesson.vtt", ext="vtt")],
        )
        options = ProcessOptions(output_root=__import__("pathlib").Path("swinydl-output"), diarization_mode="auto")
        with patch("swinydl.workflow.diarization_runtime_status", return_value=(True, None)):
            self.assertEqual(_resolve_transcript_source(options, lesson), "asr")
