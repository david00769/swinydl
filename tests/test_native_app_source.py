import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO_ROOT / "safari" / "SWinyDLSafariApp" / "Sources" / "JobStore.swift"
EXTENSION_HANDLER = (
    REPO_ROOT
    / "safari"
    / "SWinyDLSafariExtension"
    / "Sources"
    / "SafariWebExtensionHandler.swift"
)


class NativeAppSourceTests(unittest.TestCase):
    def test_model_readiness_matches_bootstrap_bundle_names(self):
        contents = APP_SOURCE.read_text(encoding="utf-8")

        for required in (
            "Preprocessor.mlmodelc",
            "Encoder.mlmodelc",
            "Decoder.mlmodelc",
            "JointDecision.mlmodelc",
            "parakeet_vocab.json",
            "Segmentation.mlmodelc",
            "FBank.mlmodelc",
            "Embedding.mlmodelc",
            "PldaRho.mlmodelc",
            "plda-parameters.json",
            "xvector-transform.json",
        ):
            self.assertIn(required, contents)

        self.assertNotIn("MelSpectrogram.mlmodelc", contents)
        self.assertNotIn("SpeakerSegmentation.mlmodelc", contents)

    def test_native_app_keeps_setup_repair_in_terminal(self):
        app_contents = APP_SOURCE.read_text(encoding="utf-8")
        ui_contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariApp"
            / "Sources"
            / "SWinyDLSafariApp.swift"
        ).read_text(encoding="utf-8")

        self.assertIn("func bootstrapModels()", app_contents)
        self.assertIn("func copyRepairCommand()", app_contents)
        self.assertNotIn("private struct SetupRepairLauncher", app_contents)
        self.assertNotIn('"--repair", "--non-interactive", "--skip-open"', app_contents)
        self.assertNotIn("process.arguments = [installScript.path", app_contents)
        self.assertIn("SWinyDLBridge.logsDirectory()", app_contents)
        self.assertIn("logDirectoryPath", app_contents)
        self.assertIn("func copySetupRepairLogPath()", app_contents)
        self.assertIn("func exportDiagnostics()", app_contents)
        self.assertIn("NSPasteboard.general.setString", app_contents)
        self.assertIn("handoffReady", app_contents)
        self.assertIn("sharedQueueAvailable", app_contents)
        self.assertIn("handoffStatusLabel", app_contents)
        self.assertIn("Ready - No queued jobs", app_contents)
        self.assertIn("missingRuntimePayload", app_contents)
        self.assertIn("isSandboxContainerPath", app_contents)
        self.assertNotIn('for parent in ["Desktop", "Downloads", "Applications"]', app_contents)
        self.assertIn("defaultOutputRoot", app_contents)
        self.assertIn("openDefaultOutputRoot", app_contents)
        self.assertIn("outputRootDisplayName", app_contents)
        self.assertIn("outputFolderReady", app_contents)
        self.assertIn("chooseOutputDirectory", app_contents)
        self.assertIn("resetOutputDirectory", app_contents)
        self.assertIn("setSavedOutputRoot", app_contents)
        self.assertIn("startAccessingSavedOutputRoot", app_contents)
        self.assertIn("outputAccessURLs", app_contents)
        self.assertIn("Copy Repair Command", ui_contents)
        self.assertIn("Export Diagnostics", ui_contents)
        self.assertIn("Choose Output", ui_contents)
        self.assertIn("Copy Log Path", ui_contents)
        self.assertIn("Safari handoff", ui_contents)
        self.assertIn("readyLabel: store.handoffStatusLabel", ui_contents)
        self.assertIn("Needs Allow", ui_contents)
        self.assertIn("OutputFolderControl", ui_contents)
        self.assertIn("subtitle: store.outputRootDisplayName", ui_contents)
        self.assertIn("Choose", ui_contents)

        repair_button_index = ui_contents.index('title: "Copy Repair Command"')
        output_row_index = ui_contents.index('title: "Output folder"')
        self.assertGreater(repair_button_index, output_row_index)

    def test_native_bridge_supports_open_app(self):
        contents = EXTENSION_HANDLER.read_text(encoding="utf-8")
        app_info = (REPO_ROOT / "safari" / "SWinyDLSafariApp" / "Info.plist").read_text(
            encoding="utf-8"
        )

        self.assertIn('operation == "open_app"', contents)
        self.assertIn("openHostApplication(context:", contents)
        self.assertIn("swinydl://open", contents)
        self.assertIn("CFBundleURLSchemes", app_info)
        self.assertIn("<string>swinydl</string>", app_info)
        self.assertIn('body["appOpened"] = appLaunch.succeeded', contents)
        self.assertIn('"app_launch"', contents)
        self.assertIn('"attempted": appLaunch.attempted', contents)
        self.assertIn('"succeeded": appLaunch.succeeded', contents)
        self.assertIn('"error": appLaunch.error.map { $0 as Any } ?? NSNull()', contents)
        self.assertIn("SWinyDLBridge.selectedOutputRoot", contents)
        self.assertIn('manifestPayload["output_root"]', contents)
        self.assertIn('manifestPayload["temp_root"]', contents)
        self.assertIn('manifestPayload["log_root"]', contents)
        self.assertNotIn("openApplication(at:", contents)
        self.assertIn("Safari could not open SWinyDL", contents)
        self.assertIn("copied SWinyDL folder", contents)


if __name__ == "__main__":
    unittest.main()
