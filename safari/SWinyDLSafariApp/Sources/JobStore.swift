import AppKit
import Combine
import Foundation

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

    static let idle = ModelBootstrapStatus(isRunning: false, message: nil, error: nil)
}

final class JobStore: ObservableObject {
    @Published private(set) var jobs: [JobEnvelope] = []
    @Published private(set) var modelReadiness = ModelReadiness.detect(bundle: .main)
    @Published private(set) var modelBootstrapStatus = ModelBootstrapStatus.idle
    @Published var preview: TranscriptPreview?

    private var timer: Timer?
    private var runningJobs: Set<String> = []

    func start() {
        refresh()
        guard timer == nil else { return }
        timer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            self?.refresh()
        }
    }

    func refresh() {
        modelReadiness = ModelReadiness.detect(bundle: .main)
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
                launch(job: job)
                continue
            }
            if [SWinyDLBridge.pendingStatus, SWinyDLBridge.retryStatus].contains(status.overallStatus) {
                launch(job: job)
            }
            if ["success", "failed"].contains(status.overallStatus) {
                runningJobs.remove(job.id)
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

    func previewTranscript(path: String) {
        let url = URL(fileURLWithPath: path)
        guard let contents = try? String(contentsOf: url, encoding: .utf8) else { return }
        preview = TranscriptPreview(path: path, title: url.lastPathComponent, contents: contents)
    }

    func bootstrapModels() {
        guard !modelBootstrapStatus.isRunning else { return }
        modelBootstrapStatus = ModelBootstrapStatus(
            isRunning: true,
            message: "Downloading local CoreML model bundles...",
            error: nil
        )
        let launcher = ModelBootstrapLauncher()
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let result = launcher.run()
            DispatchQueue.main.async {
                guard let self else { return }
                self.modelReadiness = ModelReadiness.detect(bundle: .main)
                if result.success {
                    self.modelBootstrapStatus = ModelBootstrapStatus(
                        isRunning: false,
                        message: result.message,
                        error: nil
                    )
                } else {
                    self.modelBootstrapStatus = ModelBootstrapStatus(
                        isRunning: false,
                        message: nil,
                        error: result.message
                    )
                }
                self.refresh()
            }
        }
    }

    private func launch(job: JobEnvelope) {
        guard !runningJobs.contains(job.id) else { return }
        runningJobs.insert(job.id)
        let launcher = BackendLauncher()
        let launchStatus = launcher.launch(manifestURL: job.manifestURL)
        if !launchStatus {
            let failed = JobStatusPayload(
                jobID: job.id.replacingOccurrences(of: ".json", with: ""),
                command: "process-manifest",
                overallStatus: "failed",
                courseTitle: job.status?.courseTitle ?? job.manifestURL.lastPathComponent,
                sourcePageURL: job.status?.sourcePageURL ?? "",
                outputRoot: job.status?.outputRoot ?? "",
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
        return "Missing model files: \(missing.joined(separator: " and ")). Use Download Models in this app or run install.sh."
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

private struct ModelBootstrapResult {
    let success: Bool
    let message: String
}

private struct ModelBootstrapLauncher {
    func run(bundle: Bundle = .main) -> ModelBootstrapResult {
        guard let repoRoot = SWinyDLRuntime.installRoot(bundle: bundle) else {
            return ModelBootstrapResult(
                success: false,
                message: "SWinyDL could not find the install folder. Copy the SWinyDL folder out of the DMG, then run install.sh from that copied folder."
            )
        }

        let envPython = ProcessInfo.processInfo.environment["SWINYDL_PYTHON"]
        let pythonBinary = envPython ?? SWinyDLRuntime.pythonPath(bundle: bundle)
        guard FileManager.default.isExecutableFile(atPath: pythonBinary) else {
            return ModelBootstrapResult(
                success: false,
                message: "SWinyDL could not find an executable Python runtime at \(pythonBinary). Run install.sh once from the copied SWinyDL folder."
            )
        }

        let process = Process()
        let tempDir = FileManager.default.temporaryDirectory
        let outputURL = tempDir.appendingPathComponent("swinydl-bootstrap-\(UUID().uuidString)-stdout.log")
        let errorURL = tempDir.appendingPathComponent("swinydl-bootstrap-\(UUID().uuidString)-stderr.log")
        FileManager.default.createFile(atPath: outputURL.path, contents: nil)
        FileManager.default.createFile(atPath: errorURL.path, contents: nil)
        guard let outputHandle = try? FileHandle(forWritingTo: outputURL),
              let errorHandle = try? FileHandle(forWritingTo: errorURL) else {
            return ModelBootstrapResult(
                success: false,
                message: "SWinyDL could not create temporary log files for model download."
            )
        }
        defer {
            try? outputHandle.close()
            try? errorHandle.close()
            try? FileManager.default.removeItem(at: outputURL)
            try? FileManager.default.removeItem(at: errorURL)
        }
        process.executableURL = URL(fileURLWithPath: pythonBinary)
        process.arguments = ["-m", "swinydl.main", "bootstrap-models"]
        process.currentDirectoryURL = repoRoot
        process.standardOutput = outputHandle
        process.standardError = errorHandle
        process.environment = (process.environment ?? ProcessInfo.processInfo.environment).merging(
            ["PYTHONPATH": repoRoot.path],
            uniquingKeysWith: { _, new in new }
        )

        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            return ModelBootstrapResult(
                success: false,
                message: "SWinyDL could not start the model downloader: \(error.localizedDescription)"
            )
        }

        try? outputHandle.synchronize()
        try? errorHandle.synchronize()
        let output = (try? String(contentsOf: outputURL, encoding: .utf8)) ?? ""
        let stderr = (try? String(contentsOf: errorURL, encoding: .utf8)) ?? ""
        if process.terminationStatus == 0 {
            return ModelBootstrapResult(
                success: true,
                message: "Model download finished. Parakeet and speaker diarizer readiness has been refreshed."
            )
        }

        let detail = ([stderr, output].filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty })
            .joined(separator: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return ModelBootstrapResult(
            success: false,
            message: detail.isEmpty ? "Model download failed with exit code \(process.terminationStatus)." : detail
        )
    }
}

private enum SWinyDLRuntime {
    static func installRoot(bundle: Bundle) -> URL? {
        let candidates = installRootCandidates(bundle: bundle)
        return candidates.first { isInstallRoot($0) }
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

    private static func installRootCandidates(bundle: Bundle) -> [URL] {
        var candidates: [URL] = []
        if let configured = bundle.object(forInfoDictionaryKey: "SWINYDLRepoRoot") as? String,
           !configured.isEmpty {
            candidates.append(URL(fileURLWithPath: configured, isDirectory: true))
        }

        let appParent = bundle.bundleURL.deletingLastPathComponent()
        candidates.append(appParent)
        candidates.append(appParent.deletingLastPathComponent())
        return candidates
    }

    private static func isInstallRoot(_ url: URL) -> Bool {
        let fileManager = FileManager.default
        let pyproject = url.appendingPathComponent("pyproject.toml").path
        let packageDir = url.appendingPathComponent("swinydl", isDirectory: true).path
        return fileManager.fileExists(atPath: pyproject)
            && fileManager.fileExists(atPath: packageDir)
    }
}
