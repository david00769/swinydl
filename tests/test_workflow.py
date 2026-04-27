from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from swinydl.echo_exceptions import TranscriptionError
from swinydl.models import CourseManifest, InspectOptions, LessonAsset, LessonManifest, ProcessOptions, TranscribeOptions
from swinydl.workflow import process_course, process_manifest, transcribe_file


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

    def test_download_and_transcribe_deletes_downloaded_media_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = ProcessOptions(
                output_root=Path(temp_dir),
                transcript_source="asr",
                requested_action="download_and_transcribe",
                delete_downloaded_media=True,
            )
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

            self.assertEqual(download_media.call_count, 1)
            self.assertEqual(summary.results[0].artifacts.downloaded_media_paths, [])

    def test_download_and_transcribe_retains_downloaded_media_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = ProcessOptions(
                output_root=Path(temp_dir),
                transcript_source="asr",
                requested_action="download_and_transcribe",
                delete_downloaded_media=False,
                keep_video=True,
            )
            media_file = Path(temp_dir) / "lesson.m4a"
            retained_audio = Path(temp_dir) / "2026-04-01__lesson-1__lesson-one__audio.m4a"
            retained_video = Path(temp_dir) / "2026-04-01__lesson-1__lesson-one__video.mp4"
            for path in (media_file, retained_audio, retained_video):
                path.write_text("media", encoding="utf-8")
            with patch("swinydl.workflow.BrowserSession", FakeBrowser), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch("swinydl.workflow.resolve_lesson_assets", side_effect=lambda _browser, lesson: lesson), patch(
                "swinydl.workflow.download_lesson_media", side_effect=[[media_file], [retained_audio, retained_video]]
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

            self.assertEqual(download_media.call_count, 2)
            self.assertEqual(
                summary.results[0].artifacts.downloaded_media_paths,
                [retained_audio, retained_video],
            )
            self.assertEqual(summary.results[0].artifacts.video_paths, [retained_video])

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

    def test_process_manifest_writes_intermediate_lesson_stages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "job.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "source_page_url": "https://swinburne.instructure.com/courses/72339/external_tools/405",
                        "course_url": "https://echo360.org.au/section/uuid/home",
                        "host": "https://echo360.org.au",
                        "selected_lesson_ids": ["lesson-1"],
                        "requested_action": "transcribe",
                        "delete_downloaded_media": True,
                        "cookies": [],
                        "course": {
                            "source_url": "https://echo360.org.au/section/uuid/home",
                            "hostname": "https://echo360.org.au",
                            "platform": "cloud",
                            "course_uuid": "uuid",
                            "course_id": None,
                            "course_title": "Cloud Course",
                            "lessons": [
                                {
                                    "lesson_id": "lesson-1",
                                    "title": "Lesson One",
                                    "date": "2026-04-01",
                                    "lesson_url": "https://echo360.org.au/lesson/lesson-1/classroom",
                                    "index": 1,
                                    "assets": [
                                        {"kind": "media", "url": "https://cdn.example/lesson-1.m4a", "ext": "m4a"}
                                    ],
                                }
                            ],
                        },
                        "output_root": temp_dir,
                        "keep_audio": False,
                        "keep_video": False,
                        "transcript_source": "asr",
                        "asr_backend": "auto",
                        "diarization_mode": "on",
                    }
                ),
                encoding="utf-8",
            )

            media_file = Path(temp_dir) / "lesson.m4a"
            media_file.write_text("media", encoding="utf-8")
            snapshots = []

            def capture_status(path, status):
                snapshots.append(status)
                path.write_text("{}", encoding="utf-8")

            with patch("swinydl.workflow.download_lesson_media", return_value=[media_file]), patch(
                "swinydl.workflow.normalize_media_to_wav", return_value=Path(temp_dir) / "lesson.wav"
            ), patch("swinydl.workflow.transcribe_audio") as transcribe, patch(
                "swinydl.workflow.write_job_status", side_effect=capture_status
            ):
                transcribe.return_value = (
                    [
                        __import__("swinydl.models", fromlist=["TranscriptSegment"]).TranscriptSegment(
                            start=0.0, end=1.0, text="Hello from ASR", speaker="S1"
                        )
                    ],
                    [],
                    "en",
                    True,
                    "parakeet",
                    "parakeet-tdt-0.6b-v3-coreml",
                )
                process_manifest(manifest_path)

            stages = [snapshot.lessons[0].stage for snapshot in snapshots if snapshot.lessons]
            self.assertIn("queued", stages)
            self.assertIn("downloading", stages)
            self.assertIn("extracting_audio", stages)
            self.assertIn("writing_files", stages)
            self.assertEqual(snapshots[-1].lessons[0].stage, "done")
            self.assertEqual(snapshots[-1].active_lesson_id, None)
            self.assertEqual(snapshots[-1].requested_action, "transcribe")
