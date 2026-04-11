from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from swinydl.echo_exceptions import TranscriptionError
from swinydl.models import CourseManifest, InspectOptions, LessonAsset, LessonManifest, ProcessOptions, TranscribeOptions
from swinydl.workflow import process_course, transcribe_file


class FakeBrowser:
    def __init__(self, *args, **kwargs):
        self.session = object()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def requests_session(self):
        class DummySession:
            pass

        return DummySession()


def fake_course() -> CourseManifest:
    return CourseManifest(
        source_url="https://swinydl.org.au/section/uuid/home",
        hostname="https://swinydl.org.au",
        platform="cloud",
        course_uuid="uuid",
        course_id=None,
        course_title="Cloud Course",
        lessons=[
            LessonManifest(
                lesson_id="lesson-1",
                title="Lesson One",
                date="2026-04-01",
                lesson_url="https://swinydl.org.au/lesson/lesson-1/classroom",
                index=1,
                assets=[LessonAsset(kind="caption", url="https://cdn.example/lesson-1.vtt", ext="vtt")],
            )
        ],
    )


class WorkflowTests(unittest.TestCase):
    def test_process_prefers_native_caption(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = ProcessOptions(output_root=Path(temp_dir), diarization_mode="off")
            with patch("swinydl.workflow.BrowserSession", FakeBrowser), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch("swinydl.workflow.resolve_lesson_assets", side_effect=lambda _browser, lesson: lesson), patch(
                "swinydl.workflow.load_native_caption_segments"
            ) as load_native, patch("swinydl.workflow.download_lesson_media") as download_media, patch(
                "swinydl.workflow.transcribe_audio"
            ) as transcribe:
                load_native.return_value = [
                    __import__("swinydl.models", fromlist=["TranscriptSegment"]).TranscriptSegment(
                        start=0.0, end=1.0, text="Hello world"
                    )
                ]
                summary = process_course("https://swinydl.org.au/section/uuid/home", options)

            self.assertEqual(summary.results[0].status, "success")
            self.assertEqual(summary.results[0].transcript_source, "native")
            download_media.assert_not_called()
            transcribe.assert_not_called()

    def test_process_force_asr_downloads_and_transcribes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = ProcessOptions(output_root=Path(temp_dir), transcript_source="asr")
            media_file = Path(temp_dir) / "lesson.m4a"
            media_file.write_text("media", encoding="utf-8")
            with patch("swinydl.workflow.BrowserSession", FakeBrowser), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch("swinydl.workflow.resolve_lesson_assets", side_effect=lambda _browser, lesson: lesson), patch(
                "swinydl.workflow.download_lesson_media", return_value=[media_file]
            ) as download_media, patch(
                "swinydl.workflow.normalize_media_to_wav", return_value=Path(temp_dir) / "lesson.wav"
            ), patch("swinydl.workflow.transcribe_audio") as transcribe:
                transcribe.return_value = (
                    [
                        __import__("swinydl.models", fromlist=["TranscriptSegment"]).TranscriptSegment(
                            start=0.0, end=1.0, text="Hello from ASR"
                        )
                    ],
                    [],
                    "en",
                    False,
                    "parakeet",
                    "parakeet-tdt-0.6b-v3-coreml",
                )
                summary = process_course("https://swinydl.org.au/section/uuid/home", options)

            self.assertEqual(summary.results[0].transcript_source, "asr")
            download_media.assert_called_once()
            transcribe.assert_called_once()

    def test_process_skips_existing_success_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            course = fake_course()
            lesson = course.lessons[0]
            course_dir = Path(temp_dir) / "cloud-course"
            course_dir.mkdir(parents=True)
            json_path = course_dir / "2026-04-01__lesson-1__lesson-one.json"
            json_path.write_text('{"status":"success","transcript_source":"native"}', encoding="utf-8")
            options = ProcessOptions(output_root=Path(temp_dir))
            with patch("swinydl.workflow.BrowserSession", FakeBrowser), patch(
                "swinydl.workflow.discover_course", return_value=course
            ):
                summary = process_course("https://swinydl.org.au/section/uuid/home", options)

            self.assertEqual(summary.results[0].status, "skipped")

    def test_transcribe_file_returns_failed_result_for_runtime_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "lecture.wav"
            source.write_text("audio", encoding="utf-8")
            with patch("swinydl.workflow.normalize_media_to_wav"), patch(
                "swinydl.workflow.transcribe_audio",
                side_effect=TranscriptionError("ASR backend failed"),
            ):
                result = transcribe_file(source, TranscribeOptions(output_root=Path(temp_dir)))

            self.assertEqual(result.status, "failed")
            self.assertIn("ASR backend failed", result.error)
