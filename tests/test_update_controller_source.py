import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATE_CONTROLLER = (
    REPO_ROOT / "safari" / "SWinyDLSafariApp" / "Sources" / "UpdateController.swift"
)
JOB_STORE = REPO_ROOT / "safari" / "SWinyDLSafariApp" / "Sources" / "JobStore.swift"
APP_VIEW = REPO_ROOT / "safari" / "SWinyDLSafariApp" / "Sources" / "SWinyDLSafariApp.swift"


class UpdateControllerSourceTests(unittest.TestCase):
    def test_update_controller_decodes_and_downloads_dmg_assets(self):
        contents = UPDATE_CONTROLLER.read_text(encoding="utf-8")

        self.assertIn("struct GitHubReleaseAsset", contents)
        self.assertIn('browserDownloadURL = "browser_download_url"', contents)
        self.assertIn('hasSuffix(".dmg")', contents)
        self.assertIn("downloadAvailableDMG", contents)
        self.assertIn(".downloadsDirectory", contents)
        self.assertIn("NSWorkspace.shared.open(destination)", contents)

    def test_update_sheet_exposes_download_dmg_action(self):
        contents = APP_VIEW.read_text(encoding="utf-8")

        self.assertIn("Download DMG", contents)
        self.assertIn("downloadAvailableDMG", contents)
        self.assertIn("release.dmgAsset", contents)

    def test_runtime_resolves_release_install_root_relative_to_app(self):
        contents = JOB_STORE.read_text(encoding="utf-8")

        self.assertIn("SWinyDLRuntime", contents)
        self.assertIn("bundle.bundleURL.deletingLastPathComponent()", contents)
        self.assertIn('appendingPathComponent(".venv/bin/python")', contents)
        self.assertIn('"PYTHONPATH": repoRoot.path', contents)


if __name__ == "__main__":
    unittest.main()
