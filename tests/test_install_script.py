import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallScriptTests(unittest.TestCase):
    def test_install_script_has_valid_shell_syntax(self):
        subprocess.run(
            ["bash", "-n", str(REPO_ROOT / "install.sh")],
            check=True,
            cwd=REPO_ROOT,
        )

    def test_install_script_documents_required_setup_steps(self):
        contents = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn("uv sync", contents)
        self.assertIn("bootstrap-models", contents)
        self.assertIn("xcodegen generate --spec safari/project.yml", contents)
        self.assertIn("xcodebuild -checkFirstLaunchStatus", contents)
        self.assertIn("Allow Unsigned Extensions", contents)
        self.assertIn("Press Enter to continue, or Ctrl-C to cancel.", contents)
