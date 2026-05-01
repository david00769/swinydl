import SwiftUI
import SafariServices

private enum AppTheme {
    static let background = Color(red: 0.965, green: 0.976, blue: 0.984)
    static let panel = Color.white
    static let panelBorder = Color(red: 0.875, green: 0.905, blue: 0.93)
    static let primaryText = Color(red: 0.10, green: 0.16, blue: 0.21)
    static let secondaryText = Color(red: 0.34, green: 0.43, blue: 0.52)
    static let mutedText = Color(red: 0.48, green: 0.56, blue: 0.63)
    static let accent = Color(red: 0.06, green: 0.46, blue: 0.43)
    static let success = Color(red: 0.10, green: 0.48, blue: 0.27)
    static let warning = Color(red: 0.70, green: 0.32, blue: 0.04)
    static let danger = Color(red: 0.70, green: 0.16, blue: 0.16)
    static let neutral = Color(red: 0.34, green: 0.42, blue: 0.48)
    static let blue = Color(red: 0.20, green: 0.42, blue: 0.66)
}

@main
struct SWinyDLSafariApp: App {
    @StateObject private var store = JobStore()
    @StateObject private var updates = UpdateController()

    var body: some Scene {
        WindowGroup("SWinyDL Safari") {
            ContentView()
                .environmentObject(store)
                .environmentObject(updates)
                .frame(minWidth: 960, minHeight: 640)
        }
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Check for Updates...") {
                    Task {
                        await updates.checkForUpdates(manual: true)
                    }
                }
            }
        }
    }
}

private struct ContentView: View {
    @EnvironmentObject private var store: JobStore
    @EnvironmentObject private var updates: UpdateController

    var body: some View {
        ZStack {
            AppTheme.background
                .ignoresSafeArea()

            VStack(spacing: 0) {
                workspaceHeader
                HStack(alignment: .top, spacing: 18) {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            if !healthBanners.isEmpty {
                                VStack(spacing: 10) {
                                    ForEach(healthBanners) { banner in
                                        InlineMessage(icon: banner.icon, text: banner.text, tint: banner.tint, compact: true)
                                    }
                                }
                            }
                            if let runningStatus = activeRunningJob?.status {
                                ActiveRunStrip(status: runningStatus)
                            }
                            if store.jobs.isEmpty {
                                compactEmptyState
                            } else {
                                jobsSection
                            }
                        }
                        .padding(.horizontal, 22)
                        .padding(.vertical, 18)
                    }
                    ScrollView {
                        inspectorPanel
                            .padding(.vertical, 18)
                    }
                    .frame(width: 300)
                    .scrollIndicators(.visible)
                    .padding(.trailing, 22)
                }
            }
        }
        .onAppear {
            store.start()
            updates.checkOnLaunch()
        }
        .alert(
            "SWinyDL Updates",
            isPresented: Binding(
                get: { updates.infoMessage != nil },
                set: { if !$0 { updates.clearInfoMessage() } }
            )
        ) {
            Button("OK", role: .cancel) {
                updates.clearInfoMessage()
            }
        } message: {
            Text(updates.infoMessage ?? "")
        }
        .sheet(item: $updates.availableRelease) { release in
            UpdateSheet(release: release)
                .environmentObject(updates)
        }
        .sheet(item: $store.preview) { preview in
            TranscriptPreviewSheet(preview: preview)
        }
    }

    private var workspaceHeader: some View {
        VStack(spacing: 0) {
            HStack(alignment: .center, spacing: 14) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("SWinyDL Safari")
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                        .foregroundStyle(AppTheme.primaryText)
                    Text("Open a logged-in Canvas or Echo360 page in Safari, then launch jobs from the extension.")
                        .font(.subheadline)
                        .foregroundStyle(AppTheme.secondaryText)
                }
                Spacer()
                HStack(spacing: 8) {
                    ToolbarPill(title: "\(store.jobs.count) jobs", systemImage: "tray.full")
                    ToolbarPill(title: "v\(updates.currentVersion)", systemImage: "arrow.trianglehead.2.clockwise.rotate.90")
                    ToolbarPill(
                        title: store.modelReadiness.ready ? "Models ready" : "Models missing",
                        systemImage: store.modelReadiness.ready ? "checkmark.circle.fill" : "shippingbox.fill",
                        tint: store.modelReadiness.ready ? AppTheme.success : AppTheme.warning
                    )
                }
            }
            .padding(.horizontal, 22)
            .padding(.vertical, 16)

            Divider()
                .overlay(Color.black.opacity(0.06))
        }
    }

    private var compactEmptyState: some View {
        DashboardCard(padding: 18, cornerRadius: 18) {
            VStack(alignment: .leading, spacing: 14) {
                Label("No jobs yet", systemImage: "sparkles")
                    .font(.title3.weight(.bold))
                Text("The app is ready. Use Safari to queue the first transcript run, then progress will appear here.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 12) {
                    EmptyStateStep(number: "1", title: "Enable the extension", detail: "Safari Settings > Extensions > SWinyDL Safari")
                    EmptyStateStep(number: "2", title: "Open your course page", detail: "Use a logged-in Canvas or Echo360 page")
                    EmptyStateStep(number: "3", title: "Launch the run", detail: "Pick lessons in the popup and start transcription")
                }
            }
        }
    }

    private var jobsSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Activity")
                        .font(.title2.weight(.bold))
                        .foregroundStyle(AppTheme.primaryText)
                    Text("Watch active runs, open transcripts, and inspect failures or retained media.")
                        .foregroundStyle(AppTheme.secondaryText)
                }
                Spacer()
                Text("\(store.jobs.count) total")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(AppTheme.secondaryText)
            }

            LazyVStack(spacing: 8) {
                ForEach(store.jobs) { job in
                    JobCard(job: job)
                }
            }
        }
    }

    private var inspectorPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !store.modelReadiness.ready {
                readinessPanel(emphasized: true)
            }

            DashboardCard(padding: 14, cornerRadius: 12) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Workspace")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.mutedText)
                        .textCase(.uppercase)
                    InspectorActionRow(title: "Refresh Jobs", systemImage: "arrow.clockwise") {
                        store.refresh()
                    }
                    InspectorActionRow(title: "Open Safari", systemImage: "safari") {
                        NSWorkspace.shared.openApplication(at: URL(fileURLWithPath: "/Applications/Safari.app"), configuration: .init()) { _, _ in
                        }
                    }
                    InspectorActionRow(title: "Open Outputs", systemImage: "folder") {
                        store.openOutput(path: jobOutputRoot)
                    }
                    InspectorActionRow(title: updates.isChecking ? "Checking..." : "Check for Updates", systemImage: "arrow.down.circle") {
                        Task {
                            await updates.checkForUpdates(manual: true)
                        }
                    }
                    InspectorActionRow(title: "Safari Extensions", systemImage: "puzzlepiece.extension") {
                        openSafariExtensionPreferences()
                    }
                }
            }

            if store.modelReadiness.ready {
                readinessPanel(emphasized: false)
            }

            DashboardCard(padding: 14, cornerRadius: 12) {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Defaults")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.mutedText)
                        .textCase(.uppercase)
                    InfoRow(title: "Primary output", value: ".txt")
                    InfoRow(title: "Also written", value: ".srt, .json")
                    InfoRow(title: "Speaker separation", value: "On by default")
                    InfoRow(title: "Media cleanup", value: "Delete after transcription")
                }
            }

            DashboardCard(padding: 14, cornerRadius: 12) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("How to start")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.mutedText)
                        .textCase(.uppercase)
                    Text("1. Enable the SWinyDL Safari extension.")
                    Text("2. Open a logged-in Canvas or Echo360 page.")
                    Text("3. Select lessons in the popup and launch the run.")
                }
                .font(.subheadline)
                .foregroundStyle(AppTheme.primaryText)
            }
        }
    }

    private func readinessPanel(emphasized: Bool) -> some View {
        DashboardCard(padding: 14, cornerRadius: 12) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("Readiness")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(AppTheme.mutedText)
                        .textCase(.uppercase)
                    Spacer()
                    StatusBadge(status: store.modelReadiness.ready ? "success" : "failed", compact: true)
                }
                ReadinessRow(title: "Parakeet ASR", ready: store.modelReadiness.parakeetReady)
                ReadinessRow(title: "Speaker diarizer", ready: store.modelReadiness.diarizerReady)
                if !store.modelReadiness.ready {
                    InlineMessage(
                        icon: "shippingbox.fill",
                        text: store.modelReadiness.summary,
                        tint: AppTheme.warning,
                        compact: true
                    )
                } else {
                    Text(store.modelReadiness.summary)
                        .font(.caption)
                        .foregroundStyle(AppTheme.secondaryText)
                }
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(emphasized ? AppTheme.warning.opacity(0.30) : Color.clear, lineWidth: 1)
        )
    }

    private func openSafariExtensionPreferences() {
        let extensionIdentifier = SWinyDLBridge.extensionBundleIdentifier
        SFSafariExtensionManager.getStateOfSafariExtension(withIdentifier: extensionIdentifier) { state, lookupError in
            DispatchQueue.main.async {
                if let lookupError {
                    updates.infoMessage = """
                    Safari could not find the SWinyDL extension.

                    \(lookupError.localizedDescription)

                    Open Safari Settings > Developer, turn on Allow unsigned extensions, then reopen SWinyDLSafariApp.app or run ./install.sh again.
                    """
                    return
                }

                SFSafariApplication.showPreferencesForExtension(withIdentifier: extensionIdentifier) { showError in
                    DispatchQueue.main.async {
                        if let showError {
                            updates.infoMessage = """
                            Safari could not open the SWinyDL extension settings.

                            \(showError.localizedDescription)

                            Open Safari Settings > Extensions manually and enable SWinyDL Safari.
                            """
                        } else if let state, !state.isEnabled {
                            updates.infoMessage = "Safari opened Extensions. Enable SWinyDL Safari before launching jobs from Canvas or Echo360."
                        }
                    }
                }
            }
        }
    }

    private var jobOutputRoot: String {
        store.jobs.compactMap { $0.status?.outputRoot }.first ?? FileManager.default.homeDirectoryForCurrentUser.path
    }

    private var activeRunningJob: JobEnvelope? {
        store.jobs.first(where: { $0.status?.overallStatus == "running" || $0.status?.overallStatus == "launching" })
    }

    private var healthBanners: [AppBanner] {
        var banners: [AppBanner] = []
        if store.jobs.isEmpty {
            banners.append(
                AppBanner(
                    icon: "safari",
                    text: "No Safari-launched jobs yet. Enable the SWinyDL extension, open a logged-in Canvas or Echo360 page, and queue a run from the popup.",
                    tint: AppTheme.accent
                )
            )
        }
        if !store.modelReadiness.ready {
            banners.append(
                AppBanner(
                    icon: "shippingbox",
                    text: store.modelReadiness.summary,
                    tint: AppTheme.warning
                )
            )
        }
        if store.jobs.contains(where: { ($0.status?.error ?? "").contains("Python backend") }) {
            banners.append(
                AppBanner(
                    icon: "bolt.trianglebadge.exclamationmark",
                    text: "One or more jobs failed before the Python backend could launch. Re-run install.sh or check the configured Python path.",
                    tint: .red
                )
            )
        }
        if store.jobs.contains(where: {
            let message = ($0.status?.error ?? "") + " " + ($0.status?.detail ?? "")
            return message.localizedCaseInsensitiveContains("model artifacts")
        }) {
            banners.append(
                AppBanner(
                    icon: "shippingbox",
                    text: "Required local CoreML model artifacts are missing. Run `swinydl bootstrap-models` and retry the failed lessons.",
                    tint: AppTheme.warning
                )
            )
        }
        return banners
    }
}

private struct UpdateSheet: View {
    @EnvironmentObject private var updates: UpdateController
    let release: GitHubRelease

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("GitHub release update available")
                .font(.title3.weight(.semibold))
            Text("Installed version: \(updates.currentVersion)")
            Text("Latest release: \(release.displayVersion)")
            Text(release.htmlURL.absoluteString)
                .font(.caption)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
            if let asset = release.dmgAsset {
                Text("DMG: \(asset.name)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            } else {
                InlineMessage(
                    icon: "exclamationmark.triangle",
                    text: "This release does not include a downloadable DMG asset.",
                    tint: Color(red: 0.84, green: 0.51, blue: 0.12),
                    compact: true
                )
            }
            ScrollView {
                Text(release.releaseNotesPreview)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
            .frame(minHeight: 180)
            HStack {
                Button("Later") {
                    updates.dismissAvailableRelease()
                }
                Spacer()
                Button("Open Release Page") {
                    updates.openReleasePage()
                }
                Button(updates.isDownloading ? "Downloading..." : "Download DMG") {
                    Task {
                        await updates.downloadAvailableDMG()
                    }
                }
                .disabled(updates.isDownloading || release.dmgAsset == nil)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(minWidth: 560, minHeight: 320)
    }
}

private struct JobCard: View {
    @EnvironmentObject private var store: JobStore
    @State private var expanded = false
    let job: JobEnvelope

    var body: some View {
        DashboardCard(padding: expanded ? 14 : 12, cornerRadius: 12) {
            VStack(alignment: .leading, spacing: expanded ? 10 : 7) {
                HStack(alignment: .top, spacing: 10) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(job.status?.courseTitle ?? job.manifestURL.lastPathComponent)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.primaryText)
                            .lineLimit(1)
                        HStack(spacing: 7) {
                            StatusBadge(status: job.status?.overallStatus ?? SWinyDLBridge.pendingStatus)
                            if let status = job.status, status.totalLessons > 0 {
                                MetaPill(title: "Lessons", value: "\(status.totalLessons)")
                            }
                            if let status = job.status, status.completedLessons > 0 || status.overallStatus == "success" {
                                MetaPill(title: "Done", value: "\(status.completedLessons)")
                            }
                            if let status = job.status, let elapsed = status.elapsedSeconds {
                                MetaPill(title: "Elapsed", value: compactElapsed(elapsed))
                            }
                        }
                    }
                    Spacer(minLength: 8)
                    HStack(spacing: 6) {
                        if let latestTranscript = latestTXTPath {
                            SecondaryActionButton(title: "TXT", systemImage: "doc.text", compact: true) {
                                store.openOutput(path: latestTranscript)
                            }
                        }
                        if let outputRoot = job.status?.outputRoot, !outputRoot.isEmpty, expanded {
                            SecondaryActionButton(title: "Output", systemImage: "folder", compact: true) {
                                store.openOutput(path: outputRoot)
                            }
                        }
                        SecondaryActionButton(title: "Refresh", systemImage: "arrow.clockwise", compact: true) {
                            store.refresh()
                        }
                        SecondaryActionButton(title: "Retry", systemImage: "arrow.uturn.backward", compact: true) {
                            store.retry(job: job)
                        }
                        .disabled(job.status?.overallStatus != "failed")
                        SecondaryActionButton(title: expanded ? "Hide" : "Details", systemImage: expanded ? "chevron.up" : "chevron.down", compact: true) {
                            expanded.toggle()
                        }
                    }
                }

                if let status = job.status {
                    VStack(alignment: .leading, spacing: 5) {
                        HStack(alignment: .firstTextBaseline, spacing: 8) {
                            Text(summaryLabel(for: status))
                                .font(.caption.weight(.medium))
                                .foregroundStyle(AppTheme.secondaryText)
                                .lineLimit(1)
                            Text(progressLabel(for: status))
                                .font(.caption.weight(.bold))
                                .foregroundStyle(color(for: status.overallStatus))
                            Spacer()
                            if let updatedAt = status.updatedAt, !updatedAt.isEmpty {
                                Text(shortTimestamp(updatedAt))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                        ProgressView(value: Double(status.completedLessons), total: Double(max(status.totalLessons, 1)))
                            .tint(color(for: status.overallStatus))
                            .scaleEffect(x: 1, y: 0.82, anchor: .center)
                        if let compactStatusLine = compactStatusLine(for: status) {
                            Text(compactStatusLine)
                                .font(.caption)
                                .foregroundStyle(AppTheme.secondaryText)
                                .lineLimit(expanded ? 2 : 1)
                        }
                    }

                    if let error = status.error, !error.isEmpty {
                        InlineMessage(icon: "exclamationmark.triangle.fill", text: error, tint: .red, compact: true)
                    } else if status.overallStatus == "success" && expanded {
                        InlineMessage(
                            icon: "checkmark.circle.fill",
                            text: completionMessage(for: status),
                            tint: AppTheme.success,
                            compact: true
                        )
                    }

                    if expanded {
                        DetailPanel {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Run Settings")
                                    .font(.subheadline.weight(.semibold))
                                InfoRow(title: "Transcript output", value: "TXT primary")
                                InfoRow(title: "Diarization", value: (status.diarizationMode ?? "on").capitalized)
                                InfoRow(title: "Action", value: prettyAction(status.requestedAction))
                                InfoRow(
                                    title: "Media cleanup",
                                    value: (status.deleteDownloadedMedia ?? true) ? "Delete after transcription" : "Retain downloaded media"
                                )
                                InfoRow(title: "Output root", value: status.outputRoot)
                            }
                        }

                        DetailPanel {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("What Was Produced")
                                    .font(.subheadline.weight(.semibold))
                                InfoRow(title: "TXT transcripts", value: "\(txtTranscriptCount(status))")
                                InfoRow(title: "Transcript files", value: "\(status.lessons.reduce(0) { $0 + $1.transcriptFiles.count }) total")
                                InfoRow(title: "Retained media", value: "\(status.lessons.reduce(0) { $0 + $1.retainedMediaFiles.count }) files")
                                if (status.deleteDownloadedMedia ?? true) && status.requestedAction == "download_and_transcribe" {
                                    Text("Downloaded media was deleted after transcription to conserve disk space.")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }

                        VStack(spacing: 6) {
                            ForEach(status.lessons) { lesson in
                                LessonStatusCard(
                                    lesson: lesson,
                                    retryAction: {
                                        store.retry(job: job, lesson: lesson)
                                    }
                                )
                            }
                        }

                        if !status.events.isEmpty {
                            DetailPanel {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Recent Activity")
                                        .font(.subheadline.weight(.semibold))
                                    ForEach(Array(status.events.suffix(6))) { event in
                                        HStack(alignment: .top, spacing: 8) {
                                            Image(systemName: icon(for: event.level))
                                                .foregroundStyle(color(for: event.level))
                                            VStack(alignment: .leading, spacing: 1) {
                                                Text(event.message)
                                                    .font(.subheadline)
                                                Text(formatTimestamp(event.timestamp))
                                                    .font(.caption)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else {
                    InlineMessage(icon: "clock.badge", text: "Queued. Waiting for the native wrapper to launch the backend.", tint: AppTheme.warning, compact: true)
                }
            }
        }
        .overlay(alignment: .leading) {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(color(for: job.status?.overallStatus ?? SWinyDLBridge.pendingStatus))
                .frame(width: statusStripeWidth)
                .padding(.vertical, 10)
                .padding(.leading, 7)
        }
    }

    private func color(for status: String) -> Color {
        switch status {
        case "success":
            return AppTheme.success
        case "failed":
            return AppTheme.danger
        case "running", "launching":
            return AppTheme.warning
        default:
            return AppTheme.neutral
        }
    }

    private var statusStripeWidth: CGFloat {
        switch job.status?.overallStatus ?? SWinyDLBridge.pendingStatus {
        case "failed", "running", "launching", "success":
            return 4
        default:
            return 0
        }
    }

    private func progressLabel(for status: JobStatusPayload) -> String {
        let total = max(status.totalLessons, 1)
        let percent = Int((Double(status.completedLessons) / Double(total) * 100).rounded())
        return "\(percent)%"
    }

    private func completionMessage(for status: JobStatusPayload) -> String {
        let txtCount = txtTranscriptCount(status)
        let transcriptCount = status.lessons.reduce(0) { partial, lesson in
            partial + lesson.transcriptFiles.count
        }
        return "Transcription complete. \(txtCount) TXT transcripts are ready, with \(transcriptCount) total output files available."
    }

    private func summaryLabel(for status: JobStatusPayload) -> String {
        switch status.overallStatus {
        case "success":
            return "\(txtTranscriptCount(status)) TXT transcripts ready"
        case "failed":
            return "\(status.completedLessons) of \(max(status.totalLessons, 1)) lessons completed before failure"
        default:
            return "\(status.completedLessons) of \(max(status.totalLessons, 1)) lessons complete"
        }
    }

    private func txtTranscriptCount(_ status: JobStatusPayload) -> Int {
        status.lessons.reduce(0) { partial, lesson in
            partial + lesson.transcriptFiles.filter { $0.lowercased().hasSuffix(".txt") }.count
        }
    }

    private var latestTXTPath: String? {
        for lesson in job.status?.lessons ?? [] {
            if let txt = lesson.transcriptFiles.first(where: { $0.lowercased().hasSuffix(".txt") }) {
                return txt
            }
        }
        return nil
    }

    private func prettyAction(_ value: String?) -> String {
        switch value {
        case "download_and_transcribe":
            return "Download + Transcribe"
        default:
            return "Transcribe"
        }
    }

    private func formatElapsed(_ elapsed: Double) -> String {
        let totalSeconds = max(Int(elapsed.rounded()), 0)
        let hours = totalSeconds / 3600
        let minutes = (totalSeconds % 3600) / 60
        let seconds = totalSeconds % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d elapsed", hours, minutes, seconds)
        }
        return String(format: "%02d:%02d elapsed", minutes, seconds)
    }

    private func compactElapsed(_ elapsed: Double) -> String {
        let totalSeconds = max(Int(elapsed.rounded()), 0)
        let hours = totalSeconds / 3600
        let minutes = (totalSeconds % 3600) / 60
        if hours > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(minutes)m"
    }

    private func compactStatusLine(for status: JobStatusPayload) -> String? {
        var parts: [String] = []
        if let activeLessonTitle = status.activeLessonTitle, !activeLessonTitle.isEmpty, status.overallStatus == "running" {
            parts.append("Active: \(activeLessonTitle)")
        }
        if let detail = status.detail, !detail.isEmpty {
            parts.append(detail)
        }
        return parts.isEmpty ? nil : parts.joined(separator: " • ")
    }

    private func formatTimestamp(_ timestamp: String) -> String {
        timestamp.replacingOccurrences(of: "T", with: " ").replacingOccurrences(of: "Z", with: " UTC")
    }

    private func shortTimestamp(_ timestamp: String) -> String {
        let formatted = formatTimestamp(timestamp)
        return formatted.replacingOccurrences(of: " UTC", with: "")
    }

    private func icon(for level: String) -> String {
        switch level {
        case "success":
            return "checkmark.circle.fill"
        case "error":
            return "xmark.octagon.fill"
        default:
            return "clock.arrow.circlepath"
        }
    }
}

private struct LessonStatusCard: View {
    @EnvironmentObject private var store: JobStore
    let lesson: JobLessonStatus
    let retryAction: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(lesson.title)
                        .font(.subheadline.weight(.semibold))
                    HStack(spacing: 6) {
                        StatusBadge(status: lesson.status, compact: true)
                        StageBadge(stage: lesson.stage)
                    }
                }
                Spacer()
                if let txtPath = txtTranscriptPath {
                    SecondaryActionButton(title: "Preview TXT", systemImage: "text.viewfinder", compact: true) {
                        store.previewTranscript(path: txtPath)
                    }
                }
                if let primaryTranscript = primaryTranscriptPath {
                    Button {
                        store.openOutput(path: primaryTranscript)
                    } label: {
                        Label("Open Transcript", systemImage: "doc.text")
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 7)
                            .background(
                                Color(red: 0.16, green: 0.56, blue: 0.31).opacity(0.12),
                                in: Capsule()
                            )
                            .foregroundStyle(Color(red: 0.16, green: 0.46, blue: 0.28))
                    }
                    .buttonStyle(.plain)
                }
                if lesson.status == "failed" {
                    SecondaryActionButton(title: "Retry Lesson", systemImage: "arrow.uturn.backward", compact: true) {
                        retryAction()
                    }
                }
                if let transcriptFolder = lesson.transcriptFolder, !transcriptFolder.isEmpty {
                    SecondaryActionButton(title: "Open Folder", systemImage: "folder.badge.gearshape", compact: true) {
                        store.openOutput(path: transcriptFolder)
                    }
                }
            }

            if let detail = lesson.detail, !detail.isEmpty {
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if !lesson.transcriptFiles.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Transcript Files")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    FlowLayout(items: orderedTranscriptFiles) { path in
                        Button {
                            if path.lowercased().hasSuffix(".txt") {
                                store.previewTranscript(path: path)
                            } else {
                                store.openOutput(path: path)
                            }
                        } label: {
                            FileChip(
                                title: URL(fileURLWithPath: path).lastPathComponent,
                                systemImage: icon(for: path),
                                emphasized: path.lowercased().hasSuffix(".txt")
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            if !lesson.retainedMediaFiles.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Retained Downloaded Media")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    FlowLayout(items: lesson.retainedMediaFiles) { path in
                        Button {
                            store.openOutput(path: path)
                        } label: {
                            FileChip(title: URL(fileURLWithPath: path).lastPathComponent, systemImage: "film")
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            if let error = lesson.error, !error.isEmpty {
                InlineMessage(icon: "exclamationmark.triangle.fill", text: error, tint: .red, compact: true)
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(AppTheme.background)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(AppTheme.panelBorder, lineWidth: 1)
        )
    }

    private func icon(for path: String) -> String {
        let suffix = URL(fileURLWithPath: path).pathExtension.lowercased()
        switch suffix {
        case "txt":
            return "doc.plaintext"
        case "srt":
            return "captions.bubble"
        case "json":
            return "curlybraces"
        default:
            return "doc"
        }
    }

    private var primaryTranscriptPath: String? {
        let preferredExtensions = ["txt", "srt", "json"]
        for ext in preferredExtensions {
            if let match = lesson.transcriptFiles.first(where: {
                URL(fileURLWithPath: $0).pathExtension.lowercased() == ext
            }) {
                return match
            }
        }
        return lesson.transcriptFiles.first
    }

    private var txtTranscriptPath: String? {
        lesson.transcriptFiles.first(where: { $0.lowercased().hasSuffix(".txt") })
    }

    private var orderedTranscriptFiles: [String] {
        lesson.transcriptFiles.sorted { lhs, rhs in
            let left = URL(fileURLWithPath: lhs).pathExtension.lowercased()
            let right = URL(fileURLWithPath: rhs).pathExtension.lowercased()
            let order = ["txt": 0, "srt": 1, "json": 2]
            return (order[left] ?? 99, lhs) < (order[right] ?? 99, rhs)
        }
    }
}

private struct DashboardCard<Content: View>: View {
    var padding: CGFloat = 20
    var cornerRadius: CGFloat = 12
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(AppTheme.panel)
            )
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(AppTheme.panelBorder, lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.035), radius: 8, x: 0, y: 3)
    }
}

private struct DetailPanel<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(AppTheme.background)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(AppTheme.panelBorder, lineWidth: 1)
            )
    }
}

private struct CompactActionCard: View {
    let title: String
    let systemImage: String
    let tint: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: systemImage)
                    .font(.body.weight(.semibold))
                    .foregroundStyle(tint)
                    .frame(width: 34, height: 34)
                    .background(tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 11, style: .continuous))
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(AppTheme.primaryText)
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color.white.opacity(0.96),
                                tint.opacity(0.05),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(Color.white.opacity(0.92), lineWidth: 1)
            )
            .shadow(color: tint.opacity(0.10), radius: 12, x: 0, y: 8)
        }
        .buttonStyle(.plain)
    }
}

private struct MetaPill: View {
    let title: String
    let value: String

    var body: some View {
        HStack(spacing: 6) {
            Text(title)
                .foregroundStyle(AppTheme.mutedText)
            Text(value)
                .foregroundStyle(AppTheme.primaryText)
        }
        .font(.caption.weight(.semibold))
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
        .background(AppTheme.background, in: Capsule())
    }
}

private struct HeroPill: View {
    let text: String
    let systemImage: String

    var body: some View {
        Label(text, systemImage: systemImage)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(.white.opacity(0.14), in: Capsule())
            .foregroundStyle(.white)
    }
}

private struct StatusBadge: View {
    let status: String
    var compact: Bool = false

    var body: some View {
        Text(label)
            .font(.system(size: compact ? 11 : 12, weight: .bold, design: .rounded))
            .foregroundStyle(color)
            .padding(.horizontal, compact ? 10 : 12)
            .padding(.vertical, compact ? 5 : 6)
            .background(color.opacity(0.12), in: Capsule())
    }

    private var label: String {
        switch status {
        case "queued":
            return "Queued"
        case "running":
            return "Running"
        case "success":
            return "Success"
        case "skipped":
            return "Skipped"
        case "failed":
            return "Failed"
        case "retry_requested":
            return "Retry Requested"
        default:
            return status.capitalized
        }
    }

    private var color: Color {
        switch status {
        case "success":
            return AppTheme.success
        case "skipped":
            return AppTheme.blue
        case "failed":
            return AppTheme.danger
        case "running", "launching", "retry_requested":
            return AppTheme.warning
        default:
            return AppTheme.neutral
        }
    }
}

private struct PrimaryActionButton: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .font(.headline)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Color.white, in: Capsule())
                .foregroundStyle(Color(red: 0.08, green: 0.23, blue: 0.31))
        }
        .buttonStyle(.plain)
    }
}

private struct SecondaryActionButton: View {
    @Environment(\.isEnabled) private var isEnabled
    let title: String
    let systemImage: String
    var compact: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .font((compact ? Font.caption : Font.subheadline).weight(.semibold))
                .padding(.horizontal, compact ? 10 : 14)
                .padding(.vertical, compact ? 6 : 9)
                .background(isEnabled ? Color.white : AppTheme.background, in: Capsule())
                .foregroundStyle(isEnabled ? AppTheme.primaryText : AppTheme.mutedText.opacity(0.75))
                .overlay(
                    Capsule()
                        .stroke(isEnabled ? AppTheme.panelBorder : Color.clear, lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .opacity(isEnabled ? 1.0 : 0.55)
    }
}

private struct InlineMessage: View {
    let icon: String
    let text: String
    let tint: Color
    var compact: Bool = false

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: icon)
                .foregroundStyle(tint)
                .frame(width: 16)
            Text(text)
                .font(compact ? .caption : .subheadline)
                .fontWeight(compact ? .medium : .regular)
                .foregroundStyle(messageTextColor)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(compact ? 10 : 12)
        .background(messageBackgroundColor, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(tint.opacity(0.20), lineWidth: 1)
        )
    }

    private var messageBackgroundColor: Color {
        tint.opacity(0.10)
    }

    private var messageTextColor: Color {
        tint
    }
}

private struct FileChip: View {
    let title: String
    let systemImage: String
    var emphasized: Bool = false

    var body: some View {
        Label(title, systemImage: systemImage)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(backgroundColor, in: Capsule())
            .foregroundStyle(foregroundColor)
    }

    private var backgroundColor: Color {
        emphasized
            ? AppTheme.success.opacity(0.14)
            : AppTheme.background
    }

    private var foregroundColor: Color {
        emphasized
            ? AppTheme.success
            : AppTheme.primaryText
    }
}

private struct StageBadge: View {
    let stage: String

    var body: some View {
        Text(label)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(color.opacity(0.10), in: Capsule())
            .foregroundStyle(color)
    }

    private var label: String {
        switch stage {
        case "downloading":
            return "Downloading"
        case "extracting_audio":
            return "Extracting Audio"
        case "transcribing":
            return "Transcribing"
        case "diarizing":
            return "Diarizing"
        case "writing_files":
            return "Writing Files"
        case "done":
            return "Done"
        case "failed":
            return "Failed"
        default:
            return "Queued"
        }
    }

    private var color: Color {
        switch stage {
        case "done":
            return AppTheme.success
        case "failed":
            return AppTheme.danger
        case "transcribing", "diarizing", "writing_files", "extracting_audio", "downloading":
            return AppTheme.warning
        default:
            return AppTheme.neutral
        }
    }
}

private struct TranscriptPreviewSheet: View {
    let preview: TranscriptPreview

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(preview.title)
                .font(.title3.weight(.semibold))
            Text(preview.path)
                .font(.caption)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
            ScrollView {
                Text(preview.contents)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
        }
        .padding(20)
        .frame(minWidth: 640, minHeight: 420)
    }
}

private struct ActiveRunStrip: View {
    let status: JobStatusPayload

    var body: some View {
        DashboardCard(padding: 16, cornerRadius: 18) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label("Now Processing", systemImage: "waveform.and.magnifyingglass")
                        .font(.headline)
                    Spacer()
                    StatusBadge(status: status.overallStatus)
                }
                HStack(spacing: 10) {
                    MetaPill(title: "Progress", value: "\(status.completedLessons)/\(max(status.totalLessons, 1))")
                    if let elapsed = status.elapsedSeconds {
                        MetaPill(title: "Elapsed", value: compactElapsed(elapsed))
                    }
                    if let lesson = status.activeLessonTitle, !lesson.isEmpty {
                        MetaPill(title: "Lesson", value: lesson)
                    }
                }
                ProgressView(value: Double(status.completedLessons), total: Double(max(status.totalLessons, 1)))
                    .tint(AppTheme.warning)
                if let detail = status.detail, !detail.isEmpty {
                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func compactElapsed(_ elapsed: Double) -> String {
        let totalSeconds = max(Int(elapsed.rounded()), 0)
        let hours = totalSeconds / 3600
        let minutes = (totalSeconds % 3600) / 60
        if hours > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(minutes)m"
    }
}

private struct ToolbarPill: View {
    let title: String
    let systemImage: String
    var tint: Color = AppTheme.neutral

    var body: some View {
        Label(title, systemImage: systemImage)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(AppTheme.panel, in: Capsule())
            .foregroundStyle(tint)
            .overlay(
                Capsule()
                    .stroke(Color.black.opacity(0.05), lineWidth: 1)
            )
    }
}

private struct InspectorActionRow: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: systemImage)
                    .frame(width: 18)
                    .foregroundStyle(AppTheme.accent)
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.secondary)
            }
            .foregroundStyle(AppTheme.primaryText)
            .padding(.vertical, 4)
        }
        .buttonStyle(.plain)
    }
}

private struct ReadinessRow: View {
    let title: String
    let ready: Bool

    var body: some View {
        HStack {
            Text(title)
                .foregroundStyle(AppTheme.primaryText)
            Spacer()
            Label(ready ? "Ready" : "Missing", systemImage: ready ? "checkmark.circle.fill" : "shippingbox.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(ready ? AppTheme.success : AppTheme.warning)
        }
    }
}

private struct AppBanner: Identifiable {
    let id = UUID()
    let icon: String
    let text: String
    let tint: Color
}

private struct EmptyStateStep: View {
    let number: String
    let title: String
    let detail: String

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Text(number)
                .font(.headline.weight(.bold))
                .foregroundStyle(.white)
                .frame(width: 30, height: 30)
                .background(AppTheme.accent, in: Circle())
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                Text(detail)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

private struct InfoRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title)
                .foregroundStyle(AppTheme.secondaryText)
            Spacer()
            Text(value)
                .fontWeight(.semibold)
                .foregroundStyle(AppTheme.primaryText)
        }
    }
}

private struct FlowLayout<Item: Hashable, Content: View>: View {
    let items: [Item]
    let content: (Item) -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(items.chunked(into: 3).enumerated()), id: \.offset) { _, row in
                HStack(alignment: .top, spacing: 8) {
                    ForEach(row, id: \.self) { item in
                        content(item)
                    }
                    Spacer(minLength: 0)
                }
            }
        }
    }
}

private extension Array {
    func chunked(into size: Int) -> [[Element]] {
        guard size > 0 else { return [self] }
        return stride(from: 0, to: count, by: size).map { index in
            Array(self[index..<Swift.min(index + size, count)])
        }
    }
}
