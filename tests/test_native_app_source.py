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

    def test_native_app_can_run_setup_repair_from_installer(self):
        app_contents = APP_SOURCE.read_text(encoding="utf-8")
        ui_contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariApp"
            / "Sources"
            / "SWinyDLSafariApp.swift"
        ).read_text(encoding="utf-8")

        self.assertIn("func repairSetup()", app_contents)
        self.assertIn("func bootstrapModels()", app_contents)
        self.assertIn("private struct SetupRepairLauncher", app_contents)
        self.assertIn('"--repair", "--non-interactive", "--skip-open"', app_contents)
        self.assertIn('process.executableURL = URL(fileURLWithPath: "/bin/bash")', app_contents)
        self.assertIn("SWinyDLBridge.logsDirectory()", app_contents)
        self.assertIn("logDirectoryPath", app_contents)
        self.assertIn("func openSetupRepairLogs()", app_contents)
        self.assertIn("handoffReady", app_contents)
        self.assertIn("sharedQueueAvailable", app_contents)
        self.assertIn("handoffStatusLabel", app_contents)
        self.assertIn("Ready - No queued jobs", app_contents)
        self.assertIn("missingRuntimePayload", app_contents)
        self.assertIn("This SWinyDL folder is incomplete.", app_contents)
        self.assertIn("Desktop", app_contents)
        self.assertIn("Downloads", app_contents)
        self.assertIn("defaultOutputRoot", app_contents)
        self.assertIn("openDefaultOutputRoot", app_contents)
        self.assertIn("outputRootDisplayName", app_contents)
        self.assertIn("chooseOutputDirectory", app_contents)
        self.assertIn("resetOutputDirectory", app_contents)
        self.assertIn("setSavedOutputRoot", app_contents)
        self.assertIn("startAccessingSavedOutputRoot", app_contents)
        self.assertIn("outputAccessURLs", app_contents)
        self.assertIn("Repair Setup", ui_contents)
        self.assertIn("Open Logs", ui_contents)
        self.assertIn("Safari handoff", ui_contents)
        self.assertIn("readyLabel: store.handoffStatusLabel", ui_contents)
        self.assertIn("Needs Allow", ui_contents)
        self.assertIn("OutputFolderControl", ui_contents)
        self.assertIn("subtitle: store.outputRootDisplayName", ui_contents)
        self.assertIn("Choose", ui_contents)

        repair_button_index = ui_contents.index('title: store.modelBootstrapStatus.isRunning ? "Repairing..." : "Repair Setup"')
        model_missing_branch_index = ui_contents.index("if !store.modelReadiness.ready {")
        self.assertGreater(repair_button_index, model_missing_branch_index)
        self.assertIn("} else {", ui_contents[model_missing_branch_index:repair_button_index])
        self.assertIn("if store.modelBootstrapStatus.logDirectoryPath != nil", ui_contents)

    def test_native_bridge_supports_open_app(self):
        contents = EXTENSION_HANDLER.read_text(encoding="utf-8")

        self.assertIn('case "open_app"', contents)
        self.assertIn('"appOpened": appLaunch.succeeded', contents)
        self.assertIn('"app_launch"', contents)
        self.assertIn('"attempted": true', contents)
        self.assertIn('"succeeded": appLaunch.succeeded', contents)
        self.assertIn('"error": appLaunch.error.map { $0 as Any } ?? NSNull()', contents)
        self.assertIn("SWinyDLBridge.savedOutputRoot", contents)
        self.assertIn('manifestPayload["output_root"]', contents)
        self.assertIn("private func openApp()", contents)
        self.assertIn("Safari could not find the SWinyDL app", contents)
        self.assertIn("Repair Setup", contents)


if __name__ == "__main__":
    unittest.main()
