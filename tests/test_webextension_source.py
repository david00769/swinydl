import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEBEXTENSION = REPO_ROOT / "safari" / "SWinyDLSafariExtension" / "Resources" / "WebExtension"


class WebExtensionSourceTests(unittest.TestCase):
    def test_manifest_covers_echo360_australia_iframes(self):
        manifest = json.loads((WEBEXTENSION / "manifest.json").read_text(encoding="utf-8"))
        content_script = manifest["content_scripts"][0]

        self.assertIn("*://echo360.net.au/*", manifest["host_permissions"])
        self.assertIn("*://*.echo360.net.au/*", manifest["host_permissions"])
        self.assertIn("*://echo360.net.au/*", content_script["matches"])
        self.assertIn("*://*.echo360.net.au/*", content_script["matches"])
        self.assertTrue(content_script["all_frames"])

    def test_content_script_collects_canvas_lti_launch_forms(self):
        contents = (WEBEXTENSION / "content.js").read_text(encoding="utf-8")

        self.assertIn('document.querySelectorAll("form[action]")', contents)
        self.assertIn("formActionUrls", contents)
        self.assertIn("page-context-updated", contents)
        self.assertIn("lti", contents)

    def test_background_merges_all_frame_contexts_before_detection(self):
        contents = (WEBEXTENSION / "background.js").read_text(encoding="utf-8")

        self.assertIn("tabContextCache", contents)
        self.assertIn("page-context-updated", contents)
        self.assertIn("mergePageContexts", contents)
        self.assertIn("formActionUrls", contents)
        self.assertIn("lti", contents)


if __name__ == "__main__":
    unittest.main()
