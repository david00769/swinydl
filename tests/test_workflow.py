from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from swinydl.echo_exceptions import TranscriptionError
from swinydl.models import CourseManifest, DownloadOptions, InspectOptions, LessonAsset, LessonManifest, ProcessOptions, TranscribeOptions
from swinydl.workflow import download_course, process_course, process_manifest, transcribe_file


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
    def test_course_commands_use_only_the_course_hosts_cookies(self):
        # A cookies.txt from a browser holds every site's cookies; discovery must see the
        # course host's own and parent-domain cookies and nothing else.
        seen = {}

        def fake_discover(_url, session):
            seen["cookies"] = sorted((c.domain, c.name) for c in session.cookies)
            return fake_course()

        with tempfile.TemporaryDirectory() as temp_dir:
            cookie_file = Path(temp_dir) / "cookies.txt"
            cookie_file.write_text(
                "# Netscape HTTP Cookie File\n"
                ".swinydl.org.au\tTRUE\t/\tTRUE\t0\tsso\tparent\n"
                "swinydl.org.au\tFALSE\t/\tTRUE\t0\tsession\thost\n"
                ".example.com\tTRUE\t/\tFALSE\t0\tother\tunrelated\n"
                ".mail.org.au\tTRUE\t/\tFALSE\t0\tmail\tsibling\n",
                encoding="utf-8",
            )
            options = ProcessOptions(
                output_root=Path(temp_dir) / "out", diarization_mode="off", cookies_file=cookie_file
            )
            with patch("swinydl.workflow.discover_course", side_effect=fake_discover), patch(
                "swinydl.workflow.load_native_caption_segments"
            ) as load_native, patch("swinydl.workflow.download_lesson_media"), patch(
                "swinydl.workflow.transcribe_audio"
            ):
                load_native.return_value = [
                    __import__("swinydl.models", fromlist=["TranscriptSegment"]).TranscriptSegment(
                        start=0.0, end=1.0, text="Hello world"
                    )
                ]
                summary = process_course("https://swinydl.org.au/section/uuid/home", options)

        self.assertEqual(summary.results[0].status, "success")
        self.assertEqual(seen["cookies"], [(".swinydl.org.au", "sso"), ("swinydl.org.au", "session")])

    def test_course_commands_without_cookies_explain_how_to_supply_them(self):
        from swinydl.echo_exceptions import CookieSourceError

        with tempfile.TemporaryDirectory() as temp_dir:
            options = ProcessOptions(output_root=Path(temp_dir), diarization_mode="off")
            with self.assertRaises(CookieSourceError) as raised:
                process_course("https://swinydl.org.au/section/uuid/home", options)
        self.assertIn("--cookies-from-browser", str(raised.exception))

    def test_download_uses_the_cookie_session_for_media(self):
        session = FakeBrowser()
        with tempfile.TemporaryDirectory() as temp_dir:
            options = DownloadOptions(output_root=Path(temp_dir), cookies_from_browser="safari")
            saved = Path(temp_dir) / "lesson.m4a"
            with patch("swinydl.workflow.course_session", return_value=session) as course_session, patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch("swinydl.workflow.download_lesson_media", return_value=[saved]) as download_media:
                summary = download_course("https://swinydl.org.au/section/uuid/home", options)

        course_session.assert_called_once_with(
            "https://swinydl.org.au/section/uuid/home", cookies_file=None, cookies_from_browser="safari"
        )
        self.assertIs(download_media.call_args.args[0], session)
        self.assertEqual(summary.downloads[0]["artifacts"], [str(saved)])

    def test_lesson_keys_keep_ordinary_ids_and_never_collide(self):
        from swinydl.utils import lesson_key

        uuid_id = "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b"
        self.assertEqual(lesson_key("2024-03-05", uuid_id, 1, "Week 1 Lecture"), f"2024-03-05__{uuid_id}__week-1-lecture")
        self.assertEqual(lesson_key("2024-03-05", "abc_def", 1, "t"), "2024-03-05__abc_def__t")
        long_a = "G_" + uuid_id + "_" + uuid_id + "_2024-03-05T09:00_A"
        long_b = "G_" + uuid_id + "_" + uuid_id + "_2024-03-05T09:00_B"
        key_a, key_b = lesson_key("2024-03-05", long_a, 1, "t"), lesson_key("2024-03-05", long_b, 2, "t")
        self.assertNotEqual(key_a, key_b)
        self.assertNotIn("/", lesson_key(None, "../../../escaped", 1, "t"))

    def test_process_prefers_native_caption(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            options = ProcessOptions(output_root=Path(temp_dir), diarization_mode="off")
            with patch("swinydl.workflow.course_session", lambda *_args, **_kwargs: FakeBrowser()), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch(
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
            with patch("swinydl.workflow.course_session", lambda *_args, **_kwargs: FakeBrowser()), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch(
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
            with patch("swinydl.workflow.course_session", lambda *_args, **_kwargs: FakeBrowser()), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch(
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

    def test_failed_media_download_after_asr_keeps_the_transcript(self):
        # A signed media URL can expire during a long ASR run; the transcript must survive.
        with tempfile.TemporaryDirectory() as temp_dir:
            options = ProcessOptions(
                output_root=Path(temp_dir),
                transcript_source="asr",
                requested_action="download_and_transcribe",
                delete_downloaded_media=False,
            )
            media_file = Path(temp_dir) / "lesson.m4a"
            media_file.write_text("media", encoding="utf-8")
            with patch("swinydl.workflow.course_session", lambda *_args, **_kwargs: FakeBrowser()), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch(
                "swinydl.workflow.download_lesson_media",
                side_effect=[[media_file], RuntimeError("HTTP Error 403: Forbidden (signed URL expired)")],
            ), patch(
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

            result = summary.results[0]
            self.assertEqual(result.status, "success")
            self.assertEqual(result.artifacts.txt_path.read_text(encoding="utf-8").strip(), "Hello from ASR")
            self.assertEqual(result.artifacts.downloaded_media_paths, [])

    def test_hostile_lesson_ids_stay_inside_the_output_folder_and_duplicates_run_once(self):
        course = fake_course()
        lesson = course.lessons[0]
        from dataclasses import replace as dc_replace

        course = dc_replace(
            course,
            lessons=[
                dc_replace(lesson, lesson_id="../../../escaped"),
                dc_replace(lesson, lesson_id="../../../escaped", title="Duplicate"),
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "out"
            options = ProcessOptions(output_root=output_root, diarization_mode="off")
            with patch("swinydl.workflow.course_session", lambda *_args, **_kwargs: FakeBrowser()), patch(
                "swinydl.workflow.discover_course", return_value=course
            ), patch("swinydl.workflow.load_native_caption_segments") as load_native, patch(
                "swinydl.workflow.download_lesson_media"
            ), patch("swinydl.workflow.transcribe_audio"):
                load_native.return_value = [
                    __import__("swinydl.models", fromlist=["TranscriptSegment"]).TranscriptSegment(
                        start=0.0, end=1.0, text="Hello world"
                    )
                ]
                summary = process_course("https://swinydl.org.au/section/uuid/home", options)

            self.assertEqual(len(summary.results), 1)
            txt_path = summary.results[0].artifacts.txt_path.resolve()
            self.assertTrue(txt_path.is_relative_to(output_root.resolve()))
            self.assertTrue(txt_path.exists())
            self.assertEqual([p for p in Path(temp_dir).glob("*escaped*")], [])

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
            with patch("swinydl.workflow.course_session", lambda *_args, **_kwargs: FakeBrowser()), patch(
                "swinydl.workflow.discover_course", return_value=fake_course()
            ), patch(
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
            with patch("swinydl.workflow.course_session", lambda *_args, **_kwargs: FakeBrowser()), patch(
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
                        "temp_root": str(Path(temp_dir) / "bridge-temp"),
                        "log_root": str(Path(temp_dir) / "bridge-logs"),
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
