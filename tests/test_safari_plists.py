import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PLIST = REPO_ROOT / "safari" / "SWinyDLSafariApp" / "Info.plist"
EXTENSION_PLIST = REPO_ROOT / "safari" / "SWinyDLSafariExtension" / "Info.plist"
APP_ENTITLEMENTS = REPO_ROOT / "safari" / "SWinyDLSafariApp" / "SWinyDLSafariApp.entitlements"


class SafariPlistTests(unittest.TestCase):
    def test_app_and_extension_use_release_versions_and_user_facing_names(self):
        for plist in (APP_PLIST, EXTENSION_PLIST):
            contents = plist.read_text(encoding="utf-8")

            self.assertIn("CFBundleDisplayName", contents)
            self.assertIn("SWinyDL Safari", contents)
            self.assertIn("$(MARKETING_VERSION)", contents)
            self.assertIn("$(CURRENT_PROJECT_VERSION)", contents)

    def test_extension_plist_matches_web_extension_shape(self):
        contents = EXTENSION_PLIST.read_text(encoding="utf-8")

        self.assertIn("com.apple.Safari.web-extension", contents)
        self.assertIn("SafariWebExtensionHandler", contents)
        self.assertNotIn("SFSafariWebsiteAccess", contents)

    def test_app_can_write_user_selected_output_folder(self):
        contents = APP_ENTITLEMENTS.read_text(encoding="utf-8")

        self.assertIn("com.apple.security.files.user-selected.read-write", contents)
        self.assertNotIn("com.apple.security.files.user-selected.read-only", contents)


if __name__ == "__main__":
    unittest.main()
