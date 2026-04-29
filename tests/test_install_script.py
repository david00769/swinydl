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
        self.assertIn("--build-from-source", contents)
        self.assertIn("USE_PREBUILT_APP", contents)
        self.assertIn("Using prebuilt SWinyDLSafariApp", contents)
        self.assertIn("clear_app_quarantine", contents)
        self.assertIn("sign_app_bundle", contents)
        self.assertIn("--entitlements \"$EXTENSION_ENTITLEMENTS\"", contents)
        self.assertIn("--entitlements \"$APP_ENTITLEMENTS\"", contents)
        self.assertIn("/usr/bin/codesign --verify --deep --strict", contents)
        self.assertIn("com.apple.quarantine", contents)
        self.assertIn("Contents/Resources/manifest.json", contents)
        self.assertIn("Do not double-click the .appex file directly", contents)
        self.assertIn("register_safari_extension", contents)
        self.assertIn("pluginkit -a", contents)
        self.assertIn("com.apple.Safari.web-extension", contents)
        self.assertIn("lsregister", contents)
        self.assertIn('"$BUILD_SCRIPT"', contents)
        self.assertIn("This folder does not contain a prebuilt SWinyDLSafariApp.app", contents)
        self.assertIn("xcodebuild -checkFirstLaunchStatus", contents)
        self.assertIn("Allow Unsigned Extensions", contents)
        self.assertIn("Press Enter to continue, or Ctrl-C to cancel.", contents)

    def test_install_script_has_dmg_no_compile_path(self):
        contents = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn('PREBUILT_APP_PATH="$REPO_ROOT/SWinyDLSafariApp.app"', contents)
        self.assertIn("ensure_homebrew_tools uv ffmpeg", contents)
        self.assertIn("ensure_homebrew_tools uv ffmpeg xcodegen", contents)
        self.assertIn('if [ "$USE_PREBUILT_APP" -eq 1 ]; then', contents)

    def test_build_app_script_has_valid_shell_syntax(self):
        subprocess.run(
            ["bash", "-n", str(REPO_ROOT / "scripts" / "build_app.sh")],
            check=True,
            cwd=REPO_ROOT,
        )

    def test_build_app_script_owns_swift_build(self):
        contents = (REPO_ROOT / "scripts" / "build_app.sh").read_text(encoding="utf-8")

        self.assertIn("xcodegen generate --spec safari/project.yml", contents)
        self.assertIn("xcodebuild", contents)
        self.assertIn("CODE_SIGNING_ALLOWED=NO", contents)
        self.assertIn("SWinyDLSafariExtension.entitlements", contents)
        self.assertIn("SWinyDLSafariApp.entitlements", contents)
        self.assertIn("--entitlements", contents)
        self.assertIn('OUTPUT_APP_PATH="$REPO_ROOT/SWinyDLSafariApp.app"', contents)
        self.assertIn('BUILD_ROOT="$REPO_ROOT/$BUILD_ROOT"', contents)
        self.assertIn('OUTPUT_APP_PATH="$REPO_ROOT/$OUTPUT_APP_PATH"', contents)
        self.assertIn('rm -rf "$BUILT_APP_PATH" "$BUILD_OUTPUT_DIR/SWinyDLSafariExtension.appex"', contents)
        self.assertIn('EXTENSION_RESOURCES_SRC="$REPO_ROOT/safari/SWinyDLSafariExtension/Resources/WebExtension"', contents)
        self.assertIn('EXTENSION_RESOURCES_DST="$BUILT_APP_PATH/Contents/PlugIns/SWinyDLSafariExtension.appex/Contents/Resources"', contents)
        self.assertIn("manifest.json", contents)
