from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from swinydl.auth import CookieSession
from swinydl.manifest import load_process_manifest, status_path_for_manifest
from swinydl.models import BrowserCookie
from swinydl.workflow import process_manifest


def manifest_payload(temp_dir: str) -> dict[str, object]:
    return {
        "source_page_url": "https://swinburne.instructure.com/courses/72339/external_tools/405",
        "course_url": "https://echo360.org.au/section/uuid/home",
        "host": "https://echo360.org.au",
        "selected_lesson_ids": ["lesson-1"],
        "requested_action": "transcribe",
        "delete_downloaded_media": True,
        "cookies": [
            {
                "name": "sessionid",
                "value": "abc123",
                "domain": ".echo360.org.au",
                "path": "/",
                "secure": True,
                "httpOnly": True,
            }
        ],
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
                        {
                            "kind": "caption",
                            "url": "https://cdn.example/lesson-1.vtt",
                            "ext": "vtt",
                        }
                    ],
                }
            ],
        },
        "output_root": temp_dir,
        "keep_audio": False,
        "keep_video": False,
        "transcript_source": "auto",
        "asr_backend": "auto",
        "diarization_mode": "off",
    }


class ManifestTests(unittest.TestCase):
    def test_load_process_manifest_rebuilds_course_and_cookies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "job.json"
            path.write_text(json.dumps(manifest_payload(temp_dir)), encoding="utf-8")

            manifest = load_process_manifest(path)

        self.assertEqual(manifest.selected_lesson_ids, ("lesson-1",))
        self.assertEqual(manifest.course.course_title, "Cloud Course")
        self.assertEqual(manifest.cookies[0].name, "sessionid")
        self.assertTrue(manifest.delete_downloaded_media)

    def test_cookie_session_exports_cookie_file(self):
        session = CookieSession(
            [BrowserCookie(name="sessionid", value="abc123", domain=".echo360.org.au", secure=True)]
        )

        cookie_file = Path(session.cookie_file())
        content = cookie_file.read_text(encoding="utf-8")

        self.assertIn("sessionid", content)
        self.assertIn(".echo360.org.au", content)

    def test_process_manifest_uses_manifest_course_and_writes_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "job.json"
            manifest_path.write_text(json.dumps(manifest_payload(temp_dir)), encoding="utf-8")
            with patch("swinydl.workflow.load_native_caption_segments") as load_native:
                load_native.return_value = [
                    __import__("swinydl.models", fromlist=["TranscriptSegment"]).TranscriptSegment(
                        start=0.0, end=1.0, text="Hello world"
                    )
                ]
                summary = process_manifest(manifest_path)

            self.assertEqual(summary.command, "process-manifest")
            self.assertEqual(summary.results[0].status, "success")
            status_payload = json.loads(status_path_for_manifest(manifest_path).read_text(encoding="utf-8"))
            self.assertEqual(status_payload["overall_status"], "success")
            self.assertEqual(status_payload["completed_lessons"], 1)
            self.assertEqual(status_payload["requested_action"], "transcribe")
            self.assertEqual(status_payload["diarization_mode"], "off")
            self.assertTrue(status_payload["delete_downloaded_media"])
            self.assertIsNotNone(status_payload["started_at"])
            self.assertIsNotNone(status_payload["updated_at"])
            self.assertGreaterEqual(status_payload["elapsed_seconds"], 0)
            self.assertTrue(status_payload["events"])
            self.assertEqual(status_payload["lessons"][0]["stage"], "done")
            self.assertIn("TXT transcript", status_payload["lessons"][0]["detail"])
            self.assertEqual(
                [Path(path).name for path in status_payload["lessons"][0]["transcript_files"]],
                [
                    "2026-04-01__lesson-1__lesson-one.txt",
                    "2026-04-01__lesson-1__lesson-one.srt",
                    "2026-04-01__lesson-1__lesson-one.json",
                ],
            )
            self.assertTrue(status_payload["lessons"][0]["transcript_folder"].endswith("cloud-course"))
