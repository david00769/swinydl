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
        self.assertIn("Choose Output Folder", ui_contents)
        self.assertIn("Copy Log Path", ui_contents)
        self.assertIn("Safari handoff", ui_contents)
        self.assertIn("readyLabel: store.handoffStatusLabel", ui_contents)
        self.assertIn("Needs Allow", ui_contents)
        self.assertIn("OutputFolderControl", ui_contents)
        self.assertIn("subtitle: store.outputRootDisplayName", ui_contents)
        self.assertIn("Choose", ui_contents)
        self.assertIn("Diagnostics", ui_contents)
        self.assertIn("Then use the Safari extension to queue lessons.", ui_contents)
        self.assertNotIn("Use Defaults > Output folder", ui_contents)

    def test_first_launch_output_folder_action_is_visible(self):
        ui_contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariApp"
            / "Sources"
            / "SWinyDLSafariApp.swift"
        ).read_text(encoding="utf-8")

        empty_state_index = ui_contents.index("private var compactEmptyState")
        jobs_section_index = ui_contents.index("private var jobsSection")
        empty_state = ui_contents[empty_state_index:jobs_section_index]

        self.assertIn('PrimaryActionButton(title: "Choose Output Folder"', empty_state)
        self.assertIn('SecondaryActionButton(title: "Open Safari"', empty_state)
        self.assertIn("Choose where transcripts are saved", empty_state)
        self.assertIn('InfoRow(title: "Output folder", value: store.outputRootDisplayName)', empty_state)

    def test_readiness_panel_does_not_pack_diagnostic_buttons(self):
        ui_contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariApp"
            / "Sources"
            / "SWinyDLSafariApp.swift"
        ).read_text(encoding="utf-8")

        readiness_index = ui_contents.index("private func readinessPanel")
        open_preferences_index = ui_contents.index("private func openSafariExtensionPreferences")
        readiness_panel = ui_contents[readiness_index:open_preferences_index]

        self.assertNotIn('title: "Copy Repair Command"', readiness_panel)
        self.assertNotIn('title: "Copy Log Path"', readiness_panel)
        self.assertNotIn('title: "Export Diagnostics"', readiness_panel)
        self.assertNotIn('HStack(spacing: 8) {', readiness_panel)

        diagnostics_index = ui_contents.index("private var diagnosticsPanel")
        defaults_index = ui_contents.index("private var defaultsPanel")
        diagnostics_panel = ui_contents[diagnostics_index:defaults_index]

        self.assertIn('InspectorActionRow(title: "Copy Repair Command"', diagnostics_panel)
        self.assertIn('InspectorActionRow(title: "Copy Log Path"', diagnostics_panel)
        self.assertIn('InspectorActionRow(title: "Export Diagnostics"', diagnostics_panel)

    def test_output_folder_access_uses_security_bookmark(self):
        app_contents = APP_SOURCE.read_text(encoding="utf-8")

        open_index = app_contents.index("func openDefaultOutputRoot()")
        choose_index = app_contents.index("func chooseOutputDirectory()")
        open_output = app_contents[open_index:choose_index]

        self.assertIn("SWinyDLBridge.startAccessingSavedOutputRoot(path: outputRootURL.path)", open_output)
        self.assertIn("accessURL.stopAccessingSecurityScopedResource()", open_output)
        self.assertIn("NSWorkspace.shared.open(accessURL)", open_output)
        self.assertIn("clearOutputFolderPermission", open_output)

        plain_open_index = app_contents.index("func openOutput(path: String)")
        root_path_index = app_contents.index("var outputRootPath")
        plain_open_output = app_contents[plain_open_index:root_path_index]
        self.assertIn("outputAccessScope(containing: path)", plain_open_output)
        self.assertIn("accessURL.stopAccessingSecurityScopedResource()", plain_open_output)
        self.assertIn("NSWorkspace.shared.open(url)", plain_open_output)

        preview_index = app_contents.index("func previewTranscript(path: String)")
        bootstrap_index = app_contents.index("func bootstrapModels()")
        preview_output = app_contents[preview_index:bootstrap_index]
        self.assertIn("outputAccessScope(containing: path)", preview_output)
        self.assertIn("accessURL.stopAccessingSecurityScopedResource()", preview_output)
        self.assertIn("String(contentsOf: url", preview_output)

        self.assertIn("private func outputAccessScope(containing path: String)", app_contents)
        self.assertIn("SWinyDLBridge.startAccessingSavedOutputRoot(path: outputRootURL.path)", app_contents)

    def test_choose_output_folder_verifies_bookmark_access(self):
        app_contents = APP_SOURCE.read_text(encoding="utf-8")

        choose_index = app_contents.index("func chooseOutputDirectory()")
        reset_index = app_contents.index("func resetOutputDirectory()")
        choose_output = app_contents[choose_index:reset_index]

        self.assertIn("SWinyDLBridge.setSavedOutputRoot(url)", choose_output)
        self.assertIn("SWinyDLBridge.startAccessingSavedOutputRoot(path: url.path)", choose_output)
        self.assertIn("accessURL.stopAccessingSecurityScopedResource()", choose_output)
        self.assertIn("outputFolderPermissionMessage = nil", choose_output)

    def test_output_folder_permission_failure_clears_saved_folder(self):
        app_contents = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("outputFolderPermissionMessage", app_contents)
        self.assertIn("Choose Output Folder again so SWinyDL can access this folder.", app_contents)
        self.assertIn("Choose Output Folder again so SWinyDL has permission to write transcripts.", app_contents)
        self.assertIn("private func clearOutputFolderPermission(message: String)", app_contents)
        self.assertIn("SWinyDLBridge.clearSavedOutputRoot()", app_contents)
        self.assertIn("private func redactedCookies(_ raw: Any?) -> Any", app_contents)
        self.assertIn('redacted["value"] = "[REDACTED]"', app_contents)
        self.assertNotIn('payload["cookies"] = "[REDACTED]"', app_contents)

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
        self.assertIn('"attempted": attempted', contents)
        self.assertIn('"succeeded": succeeded', contents)
        self.assertIn("recordLaunchAttempt(statusURL:", contents)
        self.assertIn("Safari extension could not open SWinyDL", contents)
        self.assertIn('"error": error.map { $0 as Any } ?? NSNull()', contents)
        self.assertIn("SWinyDLBridge.selectedOutputRoot", contents)
        self.assertIn('manifestPayload["output_root"]', contents)
        self.assertIn('manifestPayload["temp_root"]', contents)
        self.assertIn('manifestPayload["log_root"]', contents)
        self.assertNotIn("openApplication(at:", contents)
        self.assertIn("Safari could not open SWinyDL", contents)
        self.assertIn("copied SWinyDL folder", contents)

    def test_native_app_url_open_surfaces_main_window(self):
        ui_contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariApp"
            / "Sources"
            / "SWinyDLSafariApp.swift"
        ).read_text(encoding="utf-8")

        self.assertIn("@NSApplicationDelegateAdaptor(SWinyDLAppDelegate.self)", ui_contents)
        self.assertIn('WindowGroup("SWinyDL Safari")', ui_contents)
        self.assertIn('.handlesExternalEvents(matching: ["open"])', ui_contents)
        self.assertIn("@MainActor", ui_contents)
        self.assertIn("final class SWinyDLAppDelegate", ui_contents)
        self.assertIn("applicationShouldHandleReopen", ui_contents)
        self.assertIn("application(_ application: NSApplication, open urls: [URL])", ui_contents)
        self.assertIn("static func showMainWindow()", ui_contents)
        self.assertIn("NSApp.setActivationPolicy(.regular)", ui_contents)
        self.assertIn("NSApp.unhide(nil)", ui_contents)
        self.assertIn("NSApp.activate(ignoringOtherApps: true)", ui_contents)
        self.assertIn("window.makeKeyAndOrderFront(nil)", ui_contents)
        self.assertNotIn("NSHostingView(rootView: rootView)", ui_contents)
        self.assertNotIn('Selector(("newWindowForTab:"))', ui_contents)

    def test_native_job_card_has_start_and_friendly_titles(self):
        app_contents = APP_SOURCE.read_text(encoding="utf-8")
        ui_contents = (
            REPO_ROOT
            / "safari"
            / "SWinyDLSafariApp"
            / "Sources"
            / "SWinyDLSafariApp.swift"
        ).read_text(encoding="utf-8")

        self.assertIn("func start(job: JobEnvelope)", app_contents)
        self.assertIn("cleanupLaunchState(for: job.id)", app_contents)
        self.assertIn('overallStatus: "launching"', app_contents)
        self.assertIn("launchedProcesses", app_contents)
        self.assertIn("terminationHandler", app_contents)
        self.assertIn("The Python backend exited without writing a completed job status.", app_contents)
        self.assertIn("func displayInfo(for job: JobEnvelope) -> JobDisplayInfo", app_contents)
        self.assertIn("manifestDisplayInfo(for: job.manifestURL)", app_contents)
        self.assertIn("manifestLessons(for: job.manifestURL)", app_contents)
        self.assertIn("status_decode_failures", app_contents)

        self.assertIn("Text(displayInfo.title)", ui_contents)
        self.assertIn("displayInfo.subtitle", ui_contents)
        self.assertIn('SecondaryActionButton(title: "Start"', ui_contents)
        self.assertIn("store.start(job: job)", ui_contents)
        self.assertIn("job.status?.overallStatus != \"failed\"", ui_contents)


if __name__ == "__main__":
    unittest.main()
