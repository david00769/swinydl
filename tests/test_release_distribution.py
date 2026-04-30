import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleaseDistributionTests(unittest.TestCase):
    def test_package_release_script_has_valid_shell_syntax(self):
        subprocess.run(
            ["bash", "-n", str(REPO_ROOT / "scripts" / "package_release.sh")],
            check=True,
            cwd=REPO_ROOT,
        )

    def test_release_workflow_builds_and_uploads_dmg(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "release-dmg.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("tags:", workflow)
        self.assertIn("v*", workflow)
        self.assertIn("scripts/package_release.sh", workflow)
        self.assertIn("softprops/action-gh-release@v2", workflow)
        self.assertIn("dist/*.dmg", workflow)

    def test_package_release_contains_required_distribution_payload(self):
        script = (REPO_ROOT / "scripts" / "package_release.sh").read_text(encoding="utf-8")

        self.assertIn("SWinyDLSafariApp.app", script)
        self.assertIn("scripts/build_app.sh", script)
        self.assertIn("--configuration Release", script)
        self.assertIn("--output \"$APP_PATH\"", script)
        self.assertIn('--version "${VERSION#v}"', script)
        self.assertIn("parakeet-coreml-runner", script)
        self.assertIn("speaker-diarizer-coreml-runner", script)
        self.assertIn("docs/release-install.md", script)
        self.assertIn("WebExtension", script)
        self.assertIn("for dir in swinydl vendor", script)
        self.assertIn("pyproject.toml", script)
        self.assertIn("uv.lock", script)
        self.assertIn("install.sh", script)
        self.assertIn("hdiutil create", script)
        self.assertIn('-srcfolder "$STAGE_PARENT"', script)
        self.assertIn("/usr/bin/xattr -cr", script)
        self.assertIn("Contents/Resources/manifest.json", script)
        self.assertNotIn("run.sh \\", script)
        self.assertNotIn("app.py \\", script)
        self.assertNotIn("swinydl.py \\", script)
        self.assertNotIn("for dir in docs safari scripts swift", script)


if __name__ == "__main__":
    unittest.main()
