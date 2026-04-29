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
        self.assertIn("pyproject.toml", script)
        self.assertIn("uv.lock", script)
        self.assertIn("install.sh", script)
        self.assertIn("hdiutil create", script)
        self.assertIn('-srcfolder "$STAGE_PARENT"', script)
        self.assertIn("CODE_SIGNING_ALLOWED=NO", script)
        self.assertIn("/usr/bin/codesign --force --deep --sign -", script)
        self.assertIn("/usr/bin/codesign --verify --deep --strict", script)
        self.assertIn("/usr/bin/xattr -cr", script)


if __name__ == "__main__":
    unittest.main()
