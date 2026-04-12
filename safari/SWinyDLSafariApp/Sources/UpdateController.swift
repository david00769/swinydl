import AppKit
import Foundation

@MainActor
final class UpdateController: ObservableObject {
    @Published var availableRelease: GitHubRelease?
    @Published var infoMessage: String?
    @Published private(set) var isChecking = false

    let currentVersion: String

    private let repoRootURL: URL?
    private let releasesURL = URL(string: "https://github.com/david00769/swinydl/releases")!
    private var didCheckOnLaunch = false

    init(bundle: Bundle = .main) {
        repoRootURL = Self.resolveRepoRoot(bundle: bundle)
        currentVersion = Self.resolveCurrentVersion(bundle: bundle, repoRootURL: repoRootURL)
    }

    func checkOnLaunch() {
        guard !didCheckOnLaunch else { return }
        didCheckOnLaunch = true
        Task {
            await checkForUpdates(manual: false)
        }
    }

    func checkForUpdates(manual: Bool) async {
        guard !isChecking else { return }
        isChecking = true
        defer { isChecking = false }

        do {
            let release = try await GitHubReleaseService.fetchLatestRelease()
            guard shouldOffer(release: release) else {
                if manual {
                    infoMessage = "You are already on the latest GitHub release (\(currentVersion))."
                }
                return
            }
            availableRelease = release
        } catch {
            if manual {
                infoMessage = error.localizedDescription
            }
        }
    }

    func clearInfoMessage() {
        infoMessage = nil
    }

    func dismissAvailableRelease() {
        availableRelease = nil
    }

    func openReleasePage() {
        if let htmlURL = availableRelease?.htmlURL {
            NSWorkspace.shared.open(htmlURL)
            return
        }
        NSWorkspace.shared.open(releasesURL)
    }

    func openUpdateInstructions() {
        if let repoRootURL {
            let readmeURL = repoRootURL.appendingPathComponent("README.md")
            if FileManager.default.fileExists(atPath: readmeURL.path) {
                NSWorkspace.shared.open(readmeURL)
                return
            }
        }
        NSWorkspace.shared.open(releasesURL)
    }

    private func shouldOffer(release: GitHubRelease) -> Bool {
        guard let latest = SemanticVersion(release.tagName),
              let current = SemanticVersion(currentVersion)
        else {
            return true
        }
        return latest > current
    }

    private static func resolveRepoRoot(bundle: Bundle) -> URL? {
        guard let path = bundle.object(forInfoDictionaryKey: "SWINYDLRepoRoot") as? String,
              !path.isEmpty
        else {
            return nil
        }
        return URL(fileURLWithPath: path, isDirectory: true)
    }

    private static func resolveCurrentVersion(bundle: Bundle, repoRootURL: URL?) -> String {
        if let repoRootURL,
           let version = versionFromRepoRoot(repoRootURL) {
            return version
        }
        if let bundleVersion = bundle.infoDictionary?["CFBundleShortVersionString"] as? String,
           !bundleVersion.isEmpty {
            return bundleVersion
        }
        return "unknown"
    }

    private static func versionFromRepoRoot(_ repoRootURL: URL) -> String? {
        let versionFileURL = repoRootURL.appendingPathComponent("swinydl/version.py")
        guard let contents = try? String(contentsOf: versionFileURL, encoding: .utf8) else {
            return nil
        }
        for line in contents.split(separator: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard trimmed.hasPrefix("__version__") else { continue }
            guard let start = trimmed.firstIndex(of: "\""),
                  let end = trimmed[start...].dropFirst().firstIndex(of: "\"")
            else {
                continue
            }
            return String(trimmed[trimmed.index(after: start)..<end])
        }
        return nil
    }
}

struct GitHubRelease: Decodable, Identifiable {
    let tagName: String
    let htmlURL: URL
    let body: String?
    let publishedAt: Date?

    var id: String { tagName }

    var displayVersion: String {
        SemanticVersion.normalizedString(tagName)
    }

    var releaseNotesPreview: String {
        let notes = (body ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard !notes.isEmpty else {
            return "No release notes were provided for this GitHub release."
        }
        return notes
    }

    private enum CodingKeys: String, CodingKey {
        case tagName = "tag_name"
        case htmlURL = "html_url"
        case body
        case publishedAt = "published_at"
    }
}

private enum GitHubReleaseService {
    static func fetchLatestRelease() async throws -> GitHubRelease {
        guard let url = URL(string: "https://api.github.com/repos/david00769/swinydl/releases/latest") else {
            throw GitHubReleaseError.invalidURL
        }

        var request = URLRequest(url: url)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("SWinyDL Safari", forHTTPHeaderField: "User-Agent")

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw GitHubReleaseError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200:
            break
        case 404:
            throw GitHubReleaseError.noReleases
        default:
            throw GitHubReleaseError.httpStatus(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        do {
            return try decoder.decode(GitHubRelease.self, from: data)
        } catch {
            throw GitHubReleaseError.decodeFailed
        }
    }
}

private enum GitHubReleaseError: LocalizedError {
    case invalidURL
    case invalidResponse
    case noReleases
    case httpStatus(Int)
    case decodeFailed

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The GitHub release URL is invalid."
        case .invalidResponse:
            return "GitHub did not return a valid release response."
        case .noReleases:
            return "No GitHub releases were found for david00769/swinydl."
        case let .httpStatus(code):
            return "GitHub release check failed with HTTP \(code)."
        case .decodeFailed:
            return "GitHub returned release data that SWinyDL could not parse."
        }
    }
}

private struct SemanticVersion: Comparable {
    let components: [Int]

    init?(_ raw: String) {
        let normalized = Self.normalizedString(raw)
        let parts = normalized.split(separator: ".")
        guard !parts.isEmpty else { return nil }
        let numbers = parts.compactMap { Int($0) }
        guard numbers.count == parts.count else { return nil }
        components = numbers
    }

    static func < (lhs: SemanticVersion, rhs: SemanticVersion) -> Bool {
        let maxCount = max(lhs.components.count, rhs.components.count)
        for index in 0..<maxCount {
            let left = lhs.components.indices.contains(index) ? lhs.components[index] : 0
            let right = rhs.components.indices.contains(index) ? rhs.components[index] : 0
            if left != right {
                return left < right
            }
        }
        return false
    }

    static func normalizedString(_ raw: String) -> String {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.hasPrefix("v") ? String(trimmed.dropFirst()) : trimmed
    }
}
