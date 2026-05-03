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

    def test_native_app_can_repair_missing_models_from_python_bootstrapper(self):
        app_contents = APP_SOURCE.read_text(encoding="utf-8")
        ui_contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariApp"
            / "Sources"
            / "SWinyDLSafariApp.swift"
        ).read_text(encoding="utf-8")

        self.assertIn("func bootstrapModels()", app_contents)
        self.assertIn("private struct ModelBootstrapLauncher", app_contents)
        self.assertIn('"bootstrap-models"', app_contents)
        self.assertIn("Download Models", ui_contents)
        self.assertIn("Use Download Models", ui_contents)

    def test_native_bridge_supports_open_app(self):
        contents = EXTENSION_HANDLER.read_text(encoding="utf-8")

        self.assertIn('case "open_app"', contents)
        self.assertIn("private func openApp()", contents)
        self.assertIn("Safari could not find the SWinyDL app", contents)


if __name__ == "__main__":
    unittest.main()
