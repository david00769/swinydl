import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from swinydl import main
from swinydl.echo_exceptions import DiscoveryError


class CliTests(unittest.TestCase):
    def test_url_without_subcommand_defaults_to_process(self):
        summary = SimpleNamespace(
            results=[],
            course=SimpleNamespace(course_title="Course"),
        )
        with patch("swinydl.workflow.process_course", return_value=summary) as process_course:
            exit_code = main.main(["https://swinydl.org.au/section/123/home"])

        self.assertEqual(exit_code, 0)
        process_course.assert_called_once()

    def test_extract_course_helpers_still_work(self):
        from swinydl.discovery import (
            extract_course_hostname,
            extract_course_uuid,
            is_echo360_cloud_host,
        )

        self.assertEqual(
            extract_course_hostname("https://swinydl.org.au/section/123/home"),
            "https://swinydl.org.au",
        )
        self.assertTrue(is_echo360_cloud_host("https://echo360.org.au"))
        self.assertEqual(
            extract_course_uuid("https://swinydl.org.au/section/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/home", True),
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        )

    def test_cli_returns_actionable_error_for_echo360_failures(self):
        stderr = MagicMock()
        with patch("swinydl.workflow.inspect_course", side_effect=DiscoveryError("TLS certificate verification failed")), patch(
            "sys.stderr", stderr
        ):
            exit_code = main.main(["inspect", "https://swinydl.org.au/section/123/home"])

        self.assertEqual(exit_code, 2)
        stderr.write.assert_called()

    def test_process_manifest_routes_to_manifest_workflow(self):
        summary = SimpleNamespace(
            results=[],
            course=SimpleNamespace(course_title="Course"),
        )
        with patch("swinydl.workflow.process_manifest", return_value=summary) as process_manifest:
            exit_code = main.main(["process-manifest", "/tmp/job.json"])

        self.assertEqual(exit_code, 0)
        process_manifest.assert_called_once_with("/tmp/job.json")
