import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from swinydl import health


class HealthTests(unittest.TestCase):
    def test_safari_project_passes_when_generated_project_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_dir = root / "safari" / "SWinyDLSafari.xcodeproj"
            project_dir.mkdir(parents=True)
            project_file = project_dir / "project.pbxproj"
            project_file.write_text("// generated")
            spec_file = root / "safari" / "project.yml"
            spec_file.write_text("name: SWinyDLSafari")

            with patch("swinydl.health.safari_project_path", return_value=project_dir), patch(
                "swinydl.health.safari_project_spec_path", return_value=spec_file
            ):
                check = health._check_safari_project()

        self.assertEqual(check["status"], "pass")
        self.assertIn("Generated Safari Xcode project", check["summary"])

    def test_safari_build_warns_when_app_bundle_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_bundle = root / "safari" / ".build" / "Debug" / "SWinyDLSafariApp.app"
            extension_bundle = app_bundle / "Contents" / "PlugIns" / "SWinyDLSafariExtension.appex"

            with patch("swinydl.health.safari_built_app_path", return_value=app_bundle), patch(
                "swinydl.health.safari_extension_bundle_path", return_value=extension_bundle
            ):
                check = health._check_safari_build()

        self.assertEqual(check["status"], "warn")
        self.assertIn("./install.sh", check["fix"])

    def test_safari_build_passes_when_app_and_extension_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extension_bundle = root / "safari" / ".build" / "Debug" / "SWinyDLSafariApp.app" / "Contents" / "PlugIns" / "SWinyDLSafariExtension.appex"
            extension_bundle.mkdir(parents=True)
            app_bundle = extension_bundle.parents[2]

            with patch("swinydl.health.safari_built_app_path", return_value=app_bundle), patch(
                "swinydl.health.safari_extension_bundle_path", return_value=extension_bundle
            ):
                check = health._check_safari_build()

        self.assertEqual(check["status"], "pass")
        self.assertIn("Built Safari wrapper app", check["summary"])
