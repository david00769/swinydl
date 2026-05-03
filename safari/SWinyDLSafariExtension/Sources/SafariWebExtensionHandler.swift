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
        guard var manifestPayload = payload["manifest"] as? [String: Any] else {
            return ["ok": false, "error": "Missing manifest payload."]
        }
        if (manifestPayload["output_root"] as? String)?.isEmpty != false {
            manifestPayload["output_root"] = SWinyDLBridge.savedOutputRoot(bundle: .main).path
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

        let appLaunch = launchHostApplication()

        return [
            "ok": true,
            "jobId": jobID,
            "appOpened": appLaunch.succeeded,
            "app_launch": [
                "attempted": true,
                "succeeded": appLaunch.succeeded,
                "error": appLaunch.error.map { $0 as Any } ?? NSNull(),
            ],
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
        let appLaunch = launchHostApplication()
        if appLaunch.succeeded {
            return ["ok": true]
        }
        return [
            "ok": false,
            "error": appLaunch.error ?? "Safari could not find the SWinyDL app. Open SWinyDL and run Repair Setup, or run ./install.sh from the copied SWinyDL folder, then try Open App again."
        ]
    }

    private func launchHostApplication() -> (succeeded: Bool, error: String?) {
        guard let appURL = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.davidsiroky.swinydl.SafariApp") else {
            return (
                false,
                "Safari could not find the SWinyDL app. Open SWinyDL and run Repair Setup, or run ./install.sh from the copied SWinyDL folder, then try Open App again."
            )
        }
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = true
        let semaphore = DispatchSemaphore(value: 0)
        var succeeded = false
        var errorMessage: String?
        NSWorkspace.shared.openApplication(at: appURL, configuration: configuration) { app, error in
            if let error {
                errorMessage = "Safari queued the job but macOS could not open SWinyDL: \(error.localizedDescription)"
            } else if app == nil {
                errorMessage = "Safari queued the job but macOS did not confirm SWinyDL opened."
            } else {
                succeeded = true
            }
            semaphore.signal()
        }
        if semaphore.wait(timeout: .now() + 3.0) == .timedOut {
            return (false, "Safari queued the job but could not confirm SWinyDL opened. Click Open App.")
        }
        return (succeeded, errorMessage)
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
