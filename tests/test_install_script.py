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
        self.assertIn("--repair", contents)
        self.assertIn("--non-interactive", contents)
        self.assertIn("--skip-open", contents)
        self.assertIn("USE_PREBUILT_APP", contents)
        self.assertIn("validate_runtime_payload", contents)
        self.assertIn("This SWinyDL folder is missing required runtime files", contents)
        self.assertIn("No module named 'swinydl'", contents)
        self.assertIn("Using prebuilt SWinyDLSafariApp", contents)
        self.assertIn("scrub_app_metadata", contents)
        self.assertIn("sign_app_bundle", contents)
        self.assertIn("--entitlements \"$EXTENSION_ENTITLEMENTS\"", contents)
        self.assertIn("--entitlements \"$APP_ENTITLEMENTS\"", contents)
        self.assertIn("/usr/bin/codesign --verify --deep --strict", contents)
        self.assertIn("com.apple.quarantine", contents)
        self.assertIn("/usr/bin/dot_clean -m", contents)
        self.assertIn("/usr/bin/xattr -cr", contents)
        self.assertIn("Contents/Resources/manifest.json", contents)
        self.assertIn("Do not double-click the .appex file directly", contents)
        self.assertIn("register_safari_extension", contents)
        self.assertIn("pluginkit -a", contents)
        self.assertIn("com.apple.Safari.web-extension", contents)
        self.assertIn("lsregister", contents)
        self.assertIn('"$BUILD_SCRIPT"', contents)
        self.assertIn("This folder does not contain a prebuilt SWinyDLSafariApp.app", contents)
        self.assertIn("runtime release folder does not include source-build files", contents)
        self.assertIn("xcodebuild -checkFirstLaunchStatus", contents)
        self.assertIn("Allow unsigned extensions", contents)
        self.assertIn("Press Enter to continue, or Ctrl-C to cancel.", contents)
        self.assertIn('if [ "$NON_INTERACTIVE" -eq 1 ]', contents)
        self.assertIn('if [ "$SKIP_OPEN" -eq 0 ]; then', contents)

    def test_install_script_has_dmg_no_compile_path(self):
        contents = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn('PREBUILT_APP_PATH="$REPO_ROOT/SWinyDLSafariApp.app"', contents)
        self.assertIn("ensure_homebrew_tools uv ffmpeg", contents)
        self.assertIn("ensure_homebrew_tools uv ffmpeg xcodegen", contents)
        self.assertIn('if [ "$USE_PREBUILT_APP" -eq 1 ]; then', contents)

    def test_install_script_repair_mode_does_not_build_from_source(self):
        contents = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn("--repair uses the bundled prebuilt app", contents)
        self.assertIn("Repair setup requires a prebuilt SWinyDLSafariApp.app", contents)

    def test_install_script_repair_mode_fails_before_prompt_without_prebuilt_app(self):
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "install.sh"), "--repair", "--non-interactive", "--skip-open"],
            check=False,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("Repair setup requires a prebuilt SWinyDLSafariApp.app", combined)
        self.assertNotIn("Press Enter to continue", combined)

    def test_install_script_is_tracked_executable(self):
        mode = (REPO_ROOT / "install.sh").stat().st_mode

        self.assertTrue(mode & 0o111)

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
        self.assertIn("--version X.Y.Z", contents)
        self.assertIn('MARKETING_VERSION="$APP_VERSION"', contents)
        self.assertIn('CURRENT_PROJECT_VERSION="$BUILD_NUMBER"', contents)
