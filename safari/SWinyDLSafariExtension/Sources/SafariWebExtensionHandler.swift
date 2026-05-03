import AppKit
import Foundation
import SafariServices

final class SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {
    func beginRequest(with context: NSExtensionContext) {
        let request = context.inputItems.first as? NSExtensionItem
        let payload = request?.userInfo?[SFExtensionMessageKey] as? [String: Any] ?? [:]
        let operation = payload["operation"] as? String ?? ""
        let response = NSExtensionItem()

        do {
            let body = try handle(operation: operation, payload: payload)
            response.userInfo = [SFExtensionMessageKey: body]
        } catch {
            response.userInfo = [SFExtensionMessageKey: ["ok": false, "error": String(describing: error)]]
        }

        context.completeRequest(returningItems: [response], completionHandler: nil)
    }

    private func handle(operation: String, payload: [String: Any]) throws -> [String: Any] {
        switch operation {
        case "launch_job":
            return try launchJob(payload: payload)
        case "job_status":
            return loadJobStatuses()
        case "open_output":
            return try openOutput(payload: payload)
        case "open_app":
            return openApp()
        default:
            return ["ok": false, "error": "Unsupported operation '\(operation)'."]
        }
    }

    private func launchJob(payload: [String: Any]) throws -> [String: Any] {
        guard let manifestPayload = payload["manifest"] as? [String: Any] else {
            return ["ok": false, "error": "Missing manifest payload."]
        }
        let jobID = UUID().uuidString.lowercased()
        let manifestsDir = SWinyDLBridge.manifestsDirectory()
        let manifestURL = manifestsDir.appendingPathComponent("\(jobID).json")
        let statusURL = SWinyDLBridge.statusURL(for: manifestURL)

        let data = try JSONSerialization.data(withJSONObject: manifestPayload, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: manifestURL, options: .atomic)

        let selectedLessons = extractSelectedLessons(from: manifestPayload)
        let timestamp = ISO8601DateFormatter().string(from: Date())
        let initialStatus = JobStatusPayload(
            jobID: jobID,
            command: "process-manifest",
            overallStatus: SWinyDLBridge.pendingStatus,
            courseTitle: ((manifestPayload["course"] as? [String: Any])?["course_title"] as? String) ?? "SWinyDL Safari Job",
            sourcePageURL: manifestPayload["source_page_url"] as? String ?? "",
            outputRoot: manifestPayload["output_root"] as? String ?? "",
            totalLessons: selectedLessons.count,
            completedLessons: 0,
            startedAt: nil,
            updatedAt: timestamp,
            elapsedSeconds: 0,
            activeLessonID: nil,
            activeLessonTitle: nil,
            detail: "Queued in Safari. Waiting for the native wrapper to launch the backend.",
            requestedAction: manifestPayload["requested_action"] as? String,
            diarizationMode: manifestPayload["diarization_mode"] as? String,
            deleteDownloadedMedia: manifestPayload["delete_downloaded_media"] as? Bool,
            lessons: selectedLessons,
            events: [
                JobStatusEventPayload(
                    timestamp: timestamp,
                    level: "info",
                    message: "Queued \(selectedLessons.count) lessons from Safari."
                )
            ],
            summaryPath: nil,
            error: nil
        )
        let statusData = try JSONEncoder.bridgeEncoder().encode(initialStatus)
        try statusData.write(to: statusURL, options: .atomic)

        _ = launchHostApplication()

        return [
            "ok": true,
            "jobId": jobID,
            "manifestPath": manifestURL.path,
            "statusPath": statusURL.path,
        ]
    }

    private func loadJobStatuses() -> [String: Any] {
        let manifestsDir = SWinyDLBridge.manifestsDirectory()
        let urls = (try? FileManager.default.contentsOfDirectory(at: manifestsDir, includingPropertiesForKeys: nil)) ?? []
        let statusURLs = urls.filter { $0.lastPathComponent.hasSuffix(".status.json") }
        let statuses: [[String: Any]] = statusURLs.compactMap { url in
            guard
                let data = try? Data(contentsOf: url),
                let raw = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            else {
                return nil
            }
            return raw
        }
        return ["ok": true, "jobs": statuses]
    }

    private func openOutput(payload: [String: Any]) throws -> [String: Any] {
        guard let path = payload["path"] as? String, !path.isEmpty else {
            return ["ok": false, "error": "Missing output path."]
        }
        NSWorkspace.shared.open(URL(fileURLWithPath: path, isDirectory: true))
        return ["ok": true]
    }

    private func openApp() -> [String: Any] {
        if launchHostApplication() {
            return ["ok": true]
        }
        return [
            "ok": false,
            "error": "Safari could not find the SWinyDL app. Run ./install.sh from the copied SWinyDL folder, then try Open App again."
        ]
    }

    private func launchHostApplication() -> Bool {
        guard let appURL = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.davidsiroky.swinydl.SafariApp") else {
            return false
        }
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = true
        NSWorkspace.shared.openApplication(at: appURL, configuration: configuration) { _, _ in
        }
        return true
    }

    private func extractSelectedLessons(from manifestPayload: [String: Any]) -> [JobLessonStatus] {
        let selectedIDs = (manifestPayload["selected_lesson_ids"] as? [String]) ?? []
        let lessonLookup = (((manifestPayload["course"] as? [String: Any])?["lessons"] as? [[String: Any]]) ?? [])
            .reduce(into: [String: String]()) { partial, lesson in
                guard let lessonID = lesson["lesson_id"] as? String else {
                    return
                }
                partial[lessonID] = (lesson["title"] as? String) ?? lessonID
            }

        return selectedIDs.map { lessonID in
            JobLessonStatus(
                lessonID: lessonID,
                title: lessonLookup[lessonID] ?? lessonID,
                status: SWinyDLBridge.pendingStatus,
                stage: "queued",
                detail: "Queued from the Safari popup.",
                error: nil
            )
        }
    }
}
