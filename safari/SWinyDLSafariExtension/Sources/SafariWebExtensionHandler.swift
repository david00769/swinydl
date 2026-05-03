import AppKit
import Foundation
import SafariServices

final class SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {
    func beginRequest(with context: NSExtensionContext) {
        let request = context.inputItems.first as? NSExtensionItem
        let payload = request?.userInfo?[SFExtensionMessageKey] as? [String: Any] ?? [:]
        let operation = payload["operation"] as? String ?? ""
        let response = NSExtensionItem()

        if operation == "launch_job" {
            completeLaunchJob(payload: payload, context: context, response: response)
            return
        }

        if operation == "open_app" {
            openHostApplication(context: context) { appLaunch in
                if appLaunch.succeeded {
                    self.complete(response: response, context: context, body: ["ok": true])
                } else {
                    self.complete(
                        response: response,
                        context: context,
                        body: [
                            "ok": false,
                            "error": appLaunch.error ?? "Safari could not open SWinyDL. Open SWinyDLSafariApp.app from the copied SWinyDL folder."
                        ]
                    )
                }
            }
            return
        }

        do {
            let body = try handle(operation: operation, payload: payload)
            complete(response: response, context: context, body: body)
        } catch {
            complete(response: response, context: context, body: ["ok": false, "error": String(describing: error)])
        }
    }

    private func handle(operation: String, payload: [String: Any]) throws -> [String: Any] {
        switch operation {
        case "job_status":
            return loadJobStatuses()
        case "open_output":
            return try openOutput(payload: payload)
        case "save_debug_log":
            return try saveDebugLog(payload: payload)
        default:
            return ["ok": false, "error": "Unsupported operation '\(operation)'."]
        }
    }

    private func complete(response: NSExtensionItem, context: NSExtensionContext, body: [String: Any]) {
        response.userInfo = [SFExtensionMessageKey: body]
        context.completeRequest(returningItems: [response], completionHandler: nil)
    }

    private func completeLaunchJob(payload: [String: Any], context: NSExtensionContext, response: NSExtensionItem) {
        do {
            var body = try queueJob(payload: payload)
            openHostApplication(context: context) { appLaunch in
                body["appOpened"] = appLaunch.succeeded
                body["app_launch"] = [
                    "attempted": appLaunch.attempted,
                    "succeeded": appLaunch.succeeded,
                    "error": appLaunch.error.map { $0 as Any } ?? NSNull(),
                ]
                self.complete(response: response, context: context, body: body)
            }
        } catch {
            complete(response: response, context: context, body: ["ok": false, "error": String(describing: error)])
        }
    }

    private func queueJob(payload: [String: Any]) throws -> [String: Any] {
        guard var manifestPayload = payload["manifest"] as? [String: Any] else {
            return ["ok": false, "error": "Missing manifest payload."]
        }
        let outputRoot = SWinyDLBridge.selectedOutputRoot()
        manifestPayload["output_root"] = outputRoot?.path ?? ""
        manifestPayload["temp_root"] = SWinyDLBridge.tempDirectory().path
        manifestPayload["log_root"] = SWinyDLBridge.logsDirectory().path
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
            outputRoot: outputRoot?.path ?? "",
            totalLessons: selectedLessons.count,
            completedLessons: 0,
            startedAt: nil,
            updatedAt: timestamp,
            elapsedSeconds: 0,
            activeLessonID: nil,
            activeLessonTitle: nil,
            detail: outputRoot == nil
                ? "Queued. Choose an output folder in SWinyDL to start this job."
                : "Queued in Safari. Waiting for the native wrapper to launch the backend.",
            requestedAction: manifestPayload["requested_action"] as? String,
            diarizationMode: manifestPayload["diarization_mode"] as? String,
            deleteDownloadedMedia: manifestPayload["delete_downloaded_media"] as? Bool,
            lessons: selectedLessons,
            events: [
                JobStatusEventPayload(
                    timestamp: timestamp,
                    level: "info",
                    message: outputRoot == nil
                        ? "Queued \(selectedLessons.count) lessons from Safari. Waiting for an output folder."
                        : "Queued \(selectedLessons.count) lessons from Safari."
                )
            ],
            summaryPath: nil,
            error: nil
        )
        let statusData = try JSONEncoder.bridgeEncoder().encode(initialStatus)
        try statusData.write(to: statusURL, options: .atomic)

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
        return [
            "ok": false,
            "error": "Open transcript folders from the SWinyDL app. Safari extension sandboxing does not allow this popup to open local folders directly."
        ]
    }

    private func saveDebugLog(payload: [String: Any]) throws -> [String: Any] {
        guard let debugLog = payload["debug_log"] else {
            return ["ok": false, "error": "Missing debug log payload."]
        }
        guard JSONSerialization.isValidJSONObject(debugLog) else {
            return ["ok": false, "error": "Debug log payload could not be converted to JSON."]
        }

        let filename = sanitizedDebugFilename(payload["filename"] as? String)
        let directory = try debugExportDirectory()
        let url = directory.appendingPathComponent(filename, isDirectory: false)
        let data = try JSONSerialization.data(withJSONObject: debugLog, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: .atomic)
        return [
            "ok": true,
            "filename": filename,
            "path": url.path,
            "directory": directory.path
        ]
    }

    private func debugExportDirectory() throws -> URL {
        let candidates = [
            SWinyDLBridge.debugExportsDirectory(),
            FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first?
                .appendingPathComponent("SWinyDL Debug Logs", isDirectory: true)
        ].compactMap { $0 }

        for directory in candidates {
            do {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                let probe = directory.appendingPathComponent(".swinydl-debug-probe-\(UUID().uuidString)")
                try Data().write(to: probe, options: .atomic)
                try? FileManager.default.removeItem(at: probe)
                return directory
            } catch {
                continue
            }
        }
        throw NSError(
            domain: "SWinyDLDebugExport",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "SWinyDL could not create a debug export file. Check Downloads folder permissions and try again."]
        )
    }

    private func sanitizedDebugFilename(_ rawValue: String?) -> String {
        let fallback = "swinydl-debug-\(Int(Date().timeIntervalSince1970)).json"
        let raw = rawValue?.isEmpty == false ? rawValue! : fallback
        let allowedCharacters = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: ".-_"))
        let sanitizedScalars = raw.unicodeScalars.map { scalar -> String in
            allowedCharacters.contains(scalar) ? String(scalar) : "_"
        }
        var filename = sanitizedScalars.joined()
        if filename.isEmpty || filename == "." || filename == ".." {
            filename = fallback
        }
        if !filename.lowercased().hasSuffix(".json") {
            filename += ".json"
        }
        return filename
    }

    private func openHostApplication(context: NSExtensionContext, completion: @escaping (AppLaunchAttempt) -> Void) {
        guard let appURL = URL(string: "swinydl://open") else {
            completion(AppLaunchAttempt(attempted: false, succeeded: false, error: "SWinyDL could not build its app-open URL."))
            return
        }
        context.open(appURL) { succeeded in
            if succeeded {
                completion(AppLaunchAttempt(attempted: true, succeeded: true, error: nil))
            } else {
                completion(
                    AppLaunchAttempt(
                        attempted: true,
                        succeeded: false,
                        error: "Safari queued the job but macOS did not allow the extension to open SWinyDL. Open SWinyDLSafariApp.app from the copied SWinyDL folder."
                    )
                )
            }
        }
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

private struct AppLaunchAttempt {
    let attempted: Bool
    let succeeded: Bool
    let error: String?
}
