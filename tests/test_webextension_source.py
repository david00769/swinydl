import json
import unittest
from pathlib import Path

from swinydl.version import __version__


REPO_ROOT = Path(__file__).resolve().parents[1]
WEBEXTENSION = REPO_ROOT / "safari" / "SWinyDLSafariExtension" / "Resources" / "WebExtension"


class WebExtensionSourceTests(unittest.TestCase):
    def test_manifest_version_matches_package_version(self):
        manifest = json.loads((WEBEXTENSION / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(__version__, manifest["version"])

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
        self.assertIn("data-tool-id", contents)
        self.assertIn("data-tool-path", contents)
        self.assertIn("embeddedUrls", contents)
        self.assertIn("storageUrls", contents)
        self.assertIn("lessonCandidates", contents)
        self.assertIn("page-context-updated", contents)
        self.assertIn("lti", contents)

    def test_background_merges_all_frame_contexts_before_detection(self):
        contents = (WEBEXTENSION / "background.js").read_text(encoding="utf-8")

        self.assertIn("tabContextCache", contents)
        self.assertIn("browser.scripting.executeScript", contents)
        self.assertIn("allFrames: true", contents)
        self.assertIn("page-context-updated", contents)
        self.assertIn("mergePageContexts", contents)
        self.assertIn("pageUrls", contents)
        self.assertIn("formActionUrls", contents)
        self.assertIn("embeddedUrls", contents)
        self.assertIn("storageUrls", contents)
        self.assertIn("buildCloudCourseFromPageContext", contents)
        self.assertIn("lessonCandidates", contents)
        self.assertIn("lti", contents)

    def test_popup_exposes_app_selection_and_debug_controls(self):
        html = (WEBEXTENSION / "popup.html").read_text(encoding="utf-8")
        script = (WEBEXTENSION / "popup.js").read_text(encoding="utf-8")

        self.assertIn('id="open-app"', html)
        self.assertIn('id="check-all"', html)
        self.assertIn('id="uncheck-all"', html)
        self.assertIn('id="selection-controls"', html)
        self.assertIn('id="selection-count"', html)
        self.assertIn('id="export-debug"', html)
        self.assertIn("First run", html)
        self.assertIn("Copy Repair Command", html)
        self.assertIn("access data from other apps", html)
        self.assertIn('id="handoff"', html)
        self.assertIn("Progress appears in SWinyDL", html)
        self.assertIn("Queued for transcription", html)
        self.assertIn("Debug Log", html)
        self.assertIn("open-app", script)
        self.assertIn("handoff-open-app", script)
        self.assertIn("showHandoff", script)
        self.assertIn("app_launch", script)
        self.assertIn("appOpened", script)
        self.assertIn("Progress appears in SWinyDL", script)
        self.assertIn("did not open", script)
        self.assertIn("export-debug-log", script)
        self.assertIn("sendRuntimeMessage", script)
        self.assertIn("Saved ${response.filename || filename} in ${location}.", script)
        self.assertIn("Discovering course content", script)
        self.assertNotIn("createObjectURL", script)
        self.assertNotIn("blob", script)

        course_index = html.index('id="course"')
        selection_index = html.index('id="selection-controls"')
        lesson_index = html.index('id="lesson-list"')
        self.assertLess(course_index, selection_index)
        self.assertLess(selection_index, lesson_index)

        css = (WEBEXTENSION / "popup.css").read_text(encoding="utf-8")
        self.assertIn(".header-actions button", css)
        self.assertIn("white-space: nowrap", css)
        self.assertIn("height: 36px", css)

    def test_background_builds_sanitized_debug_export(self):
        contents = (WEBEXTENSION / "background.js").read_text(encoding="utf-8")

        self.assertIn("exportDebugLogForActiveTab", contents)
        self.assertIn('sendNative("save_debug_log"', contents)
        self.assertIn("buildDebugLog", contents)
        self.assertIn("sanitizeDebugValue", contents)
        self.assertIn("sanitizeUrl", contents)
        self.assertIn("full raw HTML", contents)
        self.assertIn("[REDACTED]", contents)
        self.assertNotIn("outerHTML", contents)

    def test_native_bridge_saves_debug_export_to_logs(self):
        contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariExtension"
            / "Sources"
            / "SafariWebExtensionHandler.swift"
        ).read_text(encoding="utf-8")

        self.assertIn('case "save_debug_log"', contents)
        self.assertIn("saveDebugLog", contents)
        self.assertIn("debugExportsDirectory", contents)
        self.assertIn("SWinyDL Debug Logs", contents)
        self.assertNotIn("activateFileViewerSelecting", contents)
        self.assertIn("sanitizedDebugFilename", contents)

    def test_course_title_fallback_avoids_untitled_course(self):
        contents = (WEBEXTENSION / "background.js").read_text(encoding="utf-8")

        self.assertIn("decorateCourseDisplay", contents)
        self.assertIn("bestCourseTitle", contents)
        self.assertIn("titleCandidates", contents)
        self.assertIn("isPlaceholderCourseTitle", contents)
        self.assertIn("EchoVideo Course", contents)


if __name__ == "__main__":
    unittest.main()
