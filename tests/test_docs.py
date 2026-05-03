import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_docs_explain_unsigned_safari_temporary_extension_fallback(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        docs_index = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

        for contents in (readme, docs_index):
            self.assertIn("Add Temporary Extension", contents)
            self.assertIn("WebExtension", contents)
            self.assertIn("SWinyDL-WebExtension.zip", contents)
            self.assertIn("Safari removes temporary extensions", contents)
            self.assertIn("Allow unsigned extensions", contents)

    def test_docs_explain_runtime_only_dmg(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        release_readme = (REPO_ROOT / "docs" / "release-install.md").read_text(
            encoding="utf-8"
        )

        for contents in (readme, release_readme):
            self.assertIn("runtime", contents)
            self.assertIn("prebuilt CoreML runner", contents)
            self.assertIn("chmod +x install.sh", contents)
            self.assertIn("resource fork, Finder information", contents)
            self.assertIn("does not include", contents)
            self.assertIn("GitHub", contents)

    def test_docs_explain_first_run_app_entry_and_debug_export(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        docs_index = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")
        release_readme = (REPO_ROOT / "docs" / "release-install.md").read_text(
            encoding="utf-8"
        )

        for contents in (readme, docs_index, release_readme):
            self.assertIn("First download", contents)
            self.assertIn("Control-click", contents)
            self.assertIn("Open App", contents)
            self.assertIn("Export Debug Log", contents)


if __name__ == "__main__":
    unittest.main()
