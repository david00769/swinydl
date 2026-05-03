import AppKit
import Combine
import Foundation
import UniformTypeIdentifiers

struct TranscriptPreview: Identifiable {
    let path: String
    let title: String
    let contents: String

    var id: String { path }
}

struct ModelBootstrapStatus {
    let isRunning: Bool
    let message: String?
    let error: String?
    let logDirectoryPath: String?

    static let idle = ModelBootstrapStatus(
        isRunning: false,
        message: nil,
        error: nil,
        logDirectoryPath: nil
    )
}

final class JobStore: ObservableObject {
    @Published private(set) var jobs: [JobEnvelope] = []
    @Published private(set) var modelReadiness = ModelReadiness.detect(bundle: .main)
    @Published private(set) var handoffReady = SWinyDLBridge.sharedQueueAvailable()
    @Published private(set) var modelBootstrapStatus = ModelBootstrapStatus.idle
    @Published private(set) var outputRootURL = SWinyDLBridge.selectedOutputRoot()
    @Published var preview: TranscriptPreview?

    private var timer: Timer?
    private var runningJobs: Set<String> = []
    private var outputAccessURLs: [String: URL] = [:]

    func start() {
        refresh()
        guard timer == nil else { return }
        timer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            self?.refresh()
        }
    }

    func refresh() {
        modelReadiness = ModelReadiness.detect(bundle: .main)
        handoffReady = SWinyDLBridge.sharedQueueAvailable()
        outputRootURL = SWinyDLBridge.selectedOutputRoot()
        let manifestsDir = SWinyDLBridge.manifestsDirectory()
        let manifestURLs = (try? FileManager.default.contentsOfDirectory(
            at: manifestsDir,
            includingPropertiesForKeys: nil
        ))?
            .filter { $0.pathExtension == "json" && !$0.lastPathComponent.hasSuffix(".status.json") }
            .sorted(by: { $0.lastPathComponent > $1.lastPathComponent }) ?? []

        jobs = manifestURLs.map { manifestURL in
            let statusURL = SWinyDLBridge.statusURL(for: manifestURL)
            let status = loadStatus(from: statusURL)
            return JobEnvelope(manifestURL: manifestURL, statusURL: statusURL, status: status)
        }
        .sorted(by: { lhs, rhs in
            (lhs.status?.updatedAt ?? "") > (rhs.status?.updatedAt ?? "")
        })

        for job in jobs {
            guard let status = job.status else {
                if prepareJobForLaunchIfPossible(job) {
                    launch(job: job)
                }
                continue
            }
            if [SWinyDLBridge.pendingStatus, SWinyDLBridge.retryStatus].contains(status.overallStatus) {
                if prepareJobForLaunchIfPossible(job) {
                    launch(job: job)
                }
            }
            if ["success", "failed"].contains(status.overallStatus) {
                runningJobs.remove(job.id)
                if let accessURL = outputAccessURLs.removeValue(forKey: job.id) {
                    accessURL.stopAccessingSecurityScopedResource()
                }
            }
        }
    }

    func retry(job: JobEnvelope) {
        guard var status = job.status else { return }
        status = JobStatusPayload(
            jobID: status.jobID,
            command: status.command,
            overallStatus: SWinyDLBridge.retryStatus,
            courseTitle: status.courseTitle,
            sourcePageURL: status.sourcePageURL,
            outputRoot: status.outputRoot,
            totalLessons: status.totalLessons,
            completedLessons: 0,
            startedAt: nil,
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            elapsedSeconds: 0,
            activeLessonID: nil,
            activeLessonTitle: nil,
            detail: "Retry requested from the native app.",
            requestedAction: status.requestedAction,
            diarizationMode: status.diarizationMode,
            deleteDownloadedMedia: status.deleteDownloadedMedia,
            lessons: status.lessons.map {
                JobLessonStatus(
                    lessonID: $0.lessonID,
                    title: $0.title,
                    status: SWinyDLBridge.retryStatus,
                    stage: "queued",
                    detail: "Retry requested from the native app.",
                    error: nil
                )
            },
            events: [
                JobStatusEventPayload(
                    timestamp: ISO8601DateFormatter().string(from: Date()),
                    level: "info",
                    message: "Queued retry for the full run."
                )
            ],
            summaryPath: nil,
            error: nil
        )
        saveStatus(status, to: job.statusURL)
        runningJobs.remove(job.id)
        refresh()
    }

    func retry(job: JobEnvelope, lesson: JobLessonStatus) {
        guard let payload = try? loadManifestPayload(from: job.manifestURL) else { return }
        var manifest = payload
        manifest["selected_lesson_ids"] = [lesson.lessonID]
        if var course = manifest["course"] as? [String: Any],
           let lessons = course["lessons"] as? [[String: Any]] {
            course["lessons"] = lessons.filter { ($0["lesson_id"] as? String) == lesson.lessonID }
            manifest["course"] = course
        }
        let retryID = UUID().uuidString.lowercased()
        let manifestsDir = SWinyDLBridge.manifestsDirectory()
        let retryManifestURL = manifestsDir.appendingPathComponent("\(retryID).json")
        let retryStatusURL = SWinyDLBridge.statusURL(for: retryManifestURL)
        guard let data = try? JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys]) else {
            return
        }
        try? data.write(to: retryManifestURL, options: .atomic)
        let retryStatus = JobStatusPayload(
            jobID: retryID,
            command: "process-manifest",
            overallStatus: SWinyDLBridge.pendingStatus,
            courseTitle: job.status?.courseTitle ?? lesson.title,
            sourcePageURL: job.status?.sourcePageURL ?? "",
            outputRoot: job.status?.outputRoot ?? "",
            totalLessons: 1,
            completedLessons: 0,
            startedAt: nil,
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            elapsedSeconds: 0,
            activeLessonID: lesson.lessonID,
            activeLessonTitle: lesson.title,
            detail: "Queued lesson-level retry from the native app.",
            requestedAction: job.status?.requestedAction,
            diarizationMode: job.status?.diarizationMode,
            deleteDownloadedMedia: job.status?.deleteDownloadedMedia,
            lessons: [
                JobLessonStatus(
                    lessonID: lesson.lessonID,
                    title: lesson.title,
                    status: SWinyDLBridge.pendingStatus,
                    stage: "queued",
                    detail: "Queued lesson-level retry.",
                    error: nil
                )
            ],
            events: [
                JobStatusEventPayload(
                    timestamp: ISO8601DateFormatter().string(from: Date()),
                    level: "info",
                    message: "Queued retry for \(lesson.title)."
                )
            ],
            summaryPath: nil,
            error: nil
        )
        saveStatus(retryStatus, to: retryStatusURL)
        refresh()
    }

    func openOutput(path: String) {
        let url = URL(fileURLWithPath: path)
        NSWorkspace.shared.open(url)
    }

    var outputRootPath: String {
        outputRootURL?.path ?? "Choose an output folder"
    }

    var outputRootDisplayName: String {
        guard let outputRootURL else {
            return "Choose output folder"
        }
        let name = outputRootURL.lastPathComponent
        return name.isEmpty ? outputRootURL.path : name
    }

    var outputFolderReady: Bool {
        outputRootURL != nil
    }

    var handoffStatusLabel: String {
        guard handoffReady else {
            return "Needs Allow"
        }
        let queuedCount = jobs.filter { job in
            guard let status = job.status?.overallStatus else {
                return true
            }
            return [
                SWinyDLBridge.pendingStatus,
                SWinyDLBridge.retryStatus,
                "launching",
                "running",
            ].contains(status)
        }.count
        if queuedCount == 0 {
            return "Ready - No queued jobs"
        }
        if queuedCount == 1 {
            return "Ready - 1 queued job"
        }
        return "Ready - \(queuedCount) queued jobs"
    }

    func openDefaultOutputRoot() {
        guard let outputRootURL else {
            chooseOutputDirectory()
            return
        }
        try? FileManager.default.createDirectory(at: outputRootURL, withIntermediateDirectories: true)
        NSWorkspace.shared.open(outputRootURL)
    }

    func chooseOutputDirectory() {
        let panel = NSOpenPanel()
        panel.title = "Choose SWinyDL Output Folder"
        panel.message = "Choose where transcript files should be saved."
        panel.prompt = "Use This Folder"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        panel.directoryURL = outputRootURL ?? FileManager.default.homeDirectoryForCurrentUser

        guard panel.runModal() == .OK, let url = panel.url else {
            return
        }
        SWinyDLBridge.setSavedOutputRoot(url)
        outputRootURL = url
        repairQueuedJobsMissingOutputRoot(outputRoot: url)
        refresh()
    }

    func resetOutputDirectory() {
        SWinyDLBridge.clearSavedOutputRoot()
        outputRootURL = nil
    }

    func previewTranscript(path: String) {
        let url = URL(fileURLWithPath: path)
        guard let contents = try? String(contentsOf: url, encoding: .utf8) else { return }
        preview = TranscriptPreview(path: path, title: url.lastPathComponent, contents: contents)
    }

    func bootstrapModels() {
        copyRepairCommand()
    }

    func copyRepairCommand() {
        let command: String
        if let repoRoot = SWinyDLRuntime.installRoot(bundle: .main) {
            command = "cd \(Self.shellQuoted(repoRoot.path)) && chmod +x install.sh && ./install.sh"
        } else {
            command = "cd /path/to/SWinyDL && chmod +x install.sh && ./install.sh"
        }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(command, forType: .string)
        modelBootstrapStatus = ModelBootstrapStatus(
            isRunning: false,
            message: "Copied Terminal repair command to clipboard.",
            error: nil,
            logDirectoryPath: SWinyDLBridge.logsDirectory().path
        )
    }

    func copySetupRepairLogPath() {
        let path: String
        if let logDirectoryPath = modelBootstrapStatus.logDirectoryPath, !logDirectoryPath.isEmpty {
            path = logDirectoryPath
        } else {
            path = SWinyDLBridge.logsDirectory().path
        }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(path, forType: .string)
        modelBootstrapStatus = ModelBootstrapStatus(
            isRunning: false,
            message: "Copied Logs folder path to clipboard.",
            error: nil,
            logDirectoryPath: path
        )
    }

    func exportDiagnostics() {
        let panel = NSSavePanel()
        panel.title = "Export SWinyDL Diagnostics"
        panel.nameFieldStringValue = "swinydl-diagnostics-\(Self.timestamp()).zip"
        panel.allowedContentTypes = [.zip]
        guard panel.runModal() == .OK, let destination = panel.url else {
            return
        }

        do {
            let staging = try buildDiagnosticsStagingDirectory()
            defer { try? FileManager.default.removeItem(at: staging) }
            try createZip(from: staging, to: destination)
            modelBootstrapStatus = ModelBootstrapStatus(
                isRunning: false,
                message: "Exported diagnostics to \(destination.lastPathComponent).",
                error: nil,
                logDirectoryPath: SWinyDLBridge.logsDirectory().path
            )
        } catch {
            modelBootstrapStatus = ModelBootstrapStatus(
                isRunning: false,
                message: nil,
                error: "Diagnostics export failed. Copy Log Path for details.",
                logDirectoryPath: SWinyDLBridge.logsDirectory().path
            )
        }
    }

    private func prepareJobForLaunchIfPossible(_ job: JobEnvelope) -> Bool {
        guard let outputRootURL else {
            markNeedsOutputFolder(job)
            return false
        }
        guard (job.status?.outputRoot ?? "").isEmpty else {
            return true
        }
        updateManifest(job.manifestURL) { manifest in
            manifest["output_root"] = outputRootURL.path
            manifest["temp_root"] = SWinyDLBridge.tempDirectory().path
            manifest["log_root"] = SWinyDLBridge.logsDirectory().path
        }
        repairStatusOutputRoot(job, outputRoot: outputRootURL)
        return true
    }

    private func repairQueuedJobsMissingOutputRoot(outputRoot: URL) {
        let manifestsDir = SWinyDLBridge.manifestsDirectory()
        let manifestURLs = (try? FileManager.default.contentsOfDirectory(
            at: manifestsDir,
            includingPropertiesForKeys: nil
        ))?
            .filter { $0.pathExtension == "json" && !$0.lastPathComponent.hasSuffix(".status.json") } ?? []
        for manifestURL in manifestURLs {
            let statusURL = SWinyDLBridge.statusURL(for: manifestURL)
            let envelope = JobEnvelope(manifestURL: manifestURL, statusURL: statusURL, status: loadStatus(from: statusURL))
            if (envelope.status?.outputRoot ?? "").isEmpty {
                updateManifest(manifestURL) { manifest in
                    manifest["output_root"] = outputRoot.path
                    manifest["temp_root"] = SWinyDLBridge.tempDirectory().path
                    manifest["log_root"] = SWinyDLBridge.logsDirectory().path
                }
                repairStatusOutputRoot(envelope, outputRoot: outputRoot)
            }
        }
    }

    private func repairStatusOutputRoot(_ job: JobEnvelope, outputRoot: URL) {
        guard let status = job.status else { return }
        let repaired = JobStatusPayload(
            jobID: status.jobID,
            command: status.command,
            overallStatus: status.overallStatus,
            courseTitle: status.courseTitle,
            sourcePageURL: status.sourcePageURL,
            outputRoot: outputRoot.path,
            totalLessons: status.totalLessons,
            completedLessons: status.completedLessons,
            startedAt: status.startedAt,
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            elapsedSeconds: status.elapsedSeconds,
            activeLessonID: status.activeLessonID,
            activeLessonTitle: status.activeLessonTitle,
            detail: "Queued in Safari. Waiting for the native wrapper to launch the backend.",
            requestedAction: status.requestedAction,
            diarizationMode: status.diarizationMode,
            deleteDownloadedMedia: status.deleteDownloadedMedia,
            lessons: status.lessons,
            events: status.events,
            summaryPath: status.summaryPath,
            error: nil
        )
        saveStatus(repaired, to: job.statusURL)
    }

    private func markNeedsOutputFolder(_ job: JobEnvelope) {
        guard let status = job.status else { return }
        let detail = "Choose an output folder in SWinyDL to start this job."
        if status.detail == detail && status.outputRoot.isEmpty {
            return
        }
        let blocked = JobStatusPayload(
            jobID: status.jobID,
            command: status.command,
            overallStatus: SWinyDLBridge.pendingStatus,
            courseTitle: status.courseTitle,
            sourcePageURL: status.sourcePageURL,
            outputRoot: "",
            totalLessons: status.totalLessons,
            completedLessons: status.completedLessons,
            startedAt: status.startedAt,
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            elapsedSeconds: status.elapsedSeconds,
            activeLessonID: status.activeLessonID,
            activeLessonTitle: status.activeLessonTitle,
            detail: detail,
            requestedAction: status.requestedAction,
            diarizationMode: status.diarizationMode,
            deleteDownloadedMedia: status.deleteDownloadedMedia,
            lessons: status.lessons,
            events: status.events,
            summaryPath: status.summaryPath,
            error: nil
        )
        saveStatus(blocked, to: job.statusURL)
    }

    private func markNeedsOutputFolderPermission(_ job: JobEnvelope) {
        guard let status = job.status else { return }
        SWinyDLBridge.clearSavedOutputRoot()
        outputRootURL = nil
        let blocked = JobStatusPayload(
            jobID: status.jobID,
            command: status.command,
            overallStatus: SWinyDLBridge.pendingStatus,
            courseTitle: status.courseTitle,
            sourcePageURL: status.sourcePageURL,
            outputRoot: "",
            totalLessons: status.totalLessons,
            completedLessons: status.completedLessons,
            startedAt: status.startedAt,
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            elapsedSeconds: status.elapsedSeconds,
            activeLessonID: status.activeLessonID,
            activeLessonTitle: status.activeLessonTitle,
            detail: "Choose Output Folder again so SWinyDL has permission to write transcripts.",
            requestedAction: status.requestedAction,
            diarizationMode: status.diarizationMode,
            deleteDownloadedMedia: status.deleteDownloadedMedia,
            lessons: status.lessons,
            events: status.events,
            summaryPath: status.summaryPath,
            error: nil
        )
        saveStatus(blocked, to: job.statusURL)
    }

    private func updateManifest(_ url: URL, mutate: (inout [String: Any]) -> Void) {
        guard var manifest = try? loadManifestPayload(from: url) else { return }
        mutate(&manifest)
        guard let data = try? JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys]) else {
            return
        }
        try? data.write(to: url, options: .atomic)
    }

    private func launch(job: JobEnvelope) {
        guard !runningJobs.contains(job.id) else { return }
        runningJobs.insert(job.id)
        guard let outputRootURL else {
            markNeedsOutputFolder(job)
            runningJobs.remove(job.id)
            return
        }
        if outputAccessURLs[job.id] == nil {
            guard let accessURL = SWinyDLBridge.startAccessingSavedOutputRoot(path: outputRootURL.path) else {
                markNeedsOutputFolderPermission(job)
                runningJobs.remove(job.id)
                return
            }
            outputAccessURLs[job.id] = accessURL
        }
        let launcher = BackendLauncher()
        let launchStatus = launcher.launch(manifestURL: job.manifestURL)
        if !launchStatus {
            let failed = JobStatusPayload(
                jobID: job.id.replacingOccurrences(of: ".json", with: ""),
                command: "process-manifest",
                overallStatus: "failed",
                courseTitle: job.status?.courseTitle ?? job.manifestURL.lastPathComponent,
                sourcePageURL: job.status?.sourcePageURL ?? "",
                outputRoot: outputRootURL.path,
                totalLessons: job.status?.totalLessons ?? 0,
                completedLessons: job.status?.completedLessons ?? 0,
                startedAt: job.status?.startedAt,
                updatedAt: ISO8601DateFormatter().string(from: Date()),
                elapsedSeconds: job.status?.elapsedSeconds ?? 0,
                activeLessonID: job.status?.activeLessonID,
                activeLessonTitle: job.status?.activeLessonTitle,
                detail: "The native wrapper could not launch the Python backend.",
                requestedAction: job.status?.requestedAction,
                diarizationMode: job.status?.diarizationMode,
                deleteDownloadedMedia: job.status?.deleteDownloadedMedia,
                lessons: job.status?.lessons ?? [],
                events: job.status?.events ?? [],
                summaryPath: nil,
                error: "Unable to launch the SWinyDL Python backend from the native wrapper app."
            )
            saveStatus(failed, to: job.statusURL)
            runningJobs.remove(job.id)
        }
    }

    private func loadStatus(from url: URL) -> JobStatusPayload? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder.bridgeDecoder().decode(JobStatusPayload.self, from: data)
    }

    private func saveStatus(_ status: JobStatusPayload, to url: URL) {
        guard let data = try? JSONEncoder.bridgeEncoder().encode(status) else { return }
        try? data.write(to: url, options: .atomic)
    }

    private func loadManifestPayload(from url: URL) throws -> [String: Any] {
        let data = try Data(contentsOf: url)
        guard let payload = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw CocoaError(.coderReadCorrupt)
        }
        return payload
    }

    private func buildDiagnosticsStagingDirectory() throws -> URL {
        let fileManager = FileManager.default
        let root = fileManager.temporaryDirectory
            .appendingPathComponent("swinydl-diagnostics-\(UUID().uuidString)", isDirectory: true)
        try fileManager.createDirectory(at: root, withIntermediateDirectories: true)

        try writeSanitizedJobs(to: root.appendingPathComponent("Jobs", isDirectory: true))
        try copyDirectoryIfPresent(SWinyDLBridge.logsDirectory(), to: root.appendingPathComponent("Logs", isDirectory: true))
        try copyDirectoryIfPresent(SWinyDLBridge.debugExportsDirectory(), to: root.appendingPathComponent("DebugExports", isDirectory: true))

        let metadata: [String: Any] = [
            "created_at": ISO8601DateFormatter().string(from: Date()),
            "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "",
            "handoff_ready": handoffReady,
            "output_folder_configured": outputRootURL != nil,
            "model_readiness": [
                "parakeet": modelReadiness.parakeetReady,
                "diarizer": modelReadiness.diarizerReady,
            ],
        ]
        let data = try JSONSerialization.data(withJSONObject: metadata, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: root.appendingPathComponent("environment.json"), options: .atomic)
        return root
    }

    private func writeSanitizedJobs(to destination: URL) throws {
        let fileManager = FileManager.default
        try fileManager.createDirectory(at: destination, withIntermediateDirectories: true)
        let jobsDir = SWinyDLBridge.manifestsDirectory()
        let urls = (try? fileManager.contentsOfDirectory(at: jobsDir, includingPropertiesForKeys: nil)) ?? []
        for url in urls where url.pathExtension == "json" {
            guard
                let data = try? Data(contentsOf: url),
                var payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            else {
                continue
            }
            if payload["cookies"] != nil {
                payload["cookies"] = "[REDACTED]"
            }
            let output = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
            try output.write(to: destination.appendingPathComponent(url.lastPathComponent), options: .atomic)
        }
    }

    private func copyDirectoryIfPresent(_ source: URL, to destination: URL) throws {
        guard FileManager.default.fileExists(atPath: source.path) else { return }
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        try FileManager.default.copyItem(at: source, to: destination)
    }

    private func createZip(from staging: URL, to destination: URL) throws {
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
        process.arguments = ["-c", "-k", "--sequesterRsrc", "--keepParent", staging.path, destination.path]
        try process.run()
        process.waitUntilExit()
        if process.terminationStatus != 0 {
            throw CocoaError(.fileWriteUnknown)
        }
    }

    private static func timestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        return formatter.string(from: Date())
    }

    private static func shellQuoted(_ value: String) -> String {
        "'\(value.replacingOccurrences(of: "'", with: "'\\''"))'"
    }
}

struct ModelReadiness {
    let parakeetReady: Bool
    let diarizerReady: Bool
    let repoRootPath: String?

    var ready: Bool { parakeetReady && diarizerReady }

    var summary: String {
        if ready {
            return "Parakeet and speaker models are downloaded and ready."
        }
        var missing: [String] = []
        if !parakeetReady {
            missing.append("Parakeet")
        }
        if !diarizerReady {
            missing.append("speaker diarizer")
        }
        return "Missing model files: \(missing.joined(separator: " and "))."
    }

    static func detect(bundle: Bundle) -> ModelReadiness {
        guard let repoRootURL = SWinyDLRuntime.installRoot(bundle: bundle)
        else {
            return ModelReadiness(parakeetReady: false, diarizerReady: false, repoRootPath: nil)
        }

        let parakeetDir = repoRootURL.appendingPathComponent("vendor/parakeet-tdt-0.6b-v3-coreml", isDirectory: true)
        let diarizerDir = repoRootURL.appendingPathComponent("vendor/speaker-diarization-coreml", isDirectory: true)

        let parakeetRequired = [
            "Preprocessor.mlmodelc",
            "Encoder.mlmodelc",
            "Decoder.mlmodelc",
            "JointDecision.mlmodelc",
            "parakeet_vocab.json",
        ]
        let diarizerRequired = [
            "Segmentation.mlmodelc",
            "FBank.mlmodelc",
            "Embedding.mlmodelc",
            "PldaRho.mlmodelc",
            "plda-parameters.json",
            "xvector-transform.json",
        ]

        return ModelReadiness(
            parakeetReady: hasRequiredFiles(in: parakeetDir, required: parakeetRequired),
            diarizerReady: hasRequiredFiles(in: diarizerDir, required: diarizerRequired),
            repoRootPath: repoRootURL.path
        )
    }

    private static func hasRequiredFiles(in directory: URL, required: [String]) -> Bool {
        required.allSatisfy { relativePath in
            FileManager.default.fileExists(atPath: directory.appendingPathComponent(relativePath).path)
        }
    }
}

private struct BackendLauncher {
    func launch(manifestURL: URL) -> Bool {
        let process = Process()
        let envPython = ProcessInfo.processInfo.environment["SWINYDL_PYTHON"]
        let pythonBinary = envPython ?? SWinyDLRuntime.pythonPath(bundle: .main)

        process.executableURL = URL(fileURLWithPath: pythonBinary)
        process.arguments = ["-m", "swinydl.main", "process-manifest", manifestURL.path]
        if let repoRoot = SWinyDLRuntime.installRoot(bundle: .main) {
            process.currentDirectoryURL = repoRoot
            process.environment = (process.environment ?? ProcessInfo.processInfo.environment).merging(
                ["PYTHONPATH": repoRoot.path],
                uniquingKeysWith: { _, new in new }
            )
        }
        do {
            try process.run()
            return true
        } catch {
            return false
        }
    }
}

private enum SWinyDLRuntime {
    static func installRoot(bundle: Bundle) -> URL? {
        let candidates = installRootCandidates(bundle: bundle)
        return candidates.first { isInstallRoot($0) }
    }

    static func missingRuntimePayload(in root: URL, requirePrebuiltApp: Bool) -> [String] {
        var required = [
            "pyproject.toml",
            "uv.lock",
            "install.sh",
            "swinydl",
            "swinydl/main.py",
            "swinydl/version.py",
        ]
        if requirePrebuiltApp {
            required.append(contentsOf: [
                "SWinyDLSafariApp.app",
                "SWinyDLSafariApp.app/Contents/PlugIns/SWinyDLSafariExtension.appex/Contents/Resources/manifest.json",
                "bin/parakeet-coreml-runner",
                "bin/speaker-diarizer-coreml-runner",
            ])
        }
        return required.filter { relativePath in
            !FileManager.default.fileExists(atPath: root.appendingPathComponent(relativePath).path)
        }
    }

    static func pythonPath(bundle: Bundle) -> String {
        if let root = installRoot(bundle: bundle) {
            let venvPython = root.appendingPathComponent(".venv/bin/python")
            if FileManager.default.isExecutableFile(atPath: venvPython.path) {
                return venvPython.path
            }
        }

        if let defaultPython = bundle.object(forInfoDictionaryKey: "SWINYDLDefaultPython") as? String,
           !defaultPython.isEmpty,
           FileManager.default.isExecutableFile(atPath: defaultPython) {
            return defaultPython
        }

        return "/usr/bin/python3"
    }

    static func defaultOutputRoot(bundle: Bundle) -> URL {
        if let root = installRoot(bundle: bundle) {
            return root.appendingPathComponent("swinydl-output", isDirectory: true)
        }
        return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("swinydl-output", isDirectory: true)
    }

    private static func installRootCandidates(bundle: Bundle) -> [URL] {
        var candidates: [URL] = []
        func appendCandidate(_ url: URL) {
            let standardized = url.standardizedFileURL
            if !candidates.contains(standardized) {
                candidates.append(standardized)
            }
        }

        let appParent = bundle.bundleURL.deletingLastPathComponent()
        appendCandidate(appParent)
        appendCandidate(appParent.deletingLastPathComponent())

        if let configured = bundle.object(forInfoDictionaryKey: "SWINYDLRepoRoot") as? String,
           !configured.isEmpty {
            appendCandidate(URL(fileURLWithPath: configured, isDirectory: true))
        }
        return candidates
    }

    private static func isInstallRoot(_ url: URL) -> Bool {
        guard !SWinyDLBridge.isSandboxContainerPath(url) else {
            return false
        }
        let fileManager = FileManager.default
        let pyproject = url.appendingPathComponent("pyproject.toml").path
        let installer = url.appendingPathComponent("install.sh").path
        let appBundle = url.appendingPathComponent("SWinyDLSafariApp.app", isDirectory: true).path
        return fileManager.fileExists(atPath: pyproject)
            && (fileManager.fileExists(atPath: installer) || fileManager.fileExists(atPath: appBundle))
    }
}
