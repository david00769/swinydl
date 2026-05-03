import Foundation

enum SWinyDLBridge {
    static let appGroupIdentifier = "group.com.davidsiroky.swinydl"
    static let extensionBundleIdentifier = "com.davidsiroky.swinydl.SafariApp.Extension"
    static let pendingStatus = "queued"
    static let retryStatus = "retry_requested"

    static func sharedContainerAvailable() -> Bool {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroupIdentifier) != nil
    }

    static func containerURL() -> URL {
        guard let url = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroupIdentifier
        ) else {
            return FileManager.default.temporaryDirectory.appendingPathComponent("SWinyDLSafariBridge", isDirectory: true)
        }
        return url.appendingPathComponent("SafariBridge", isDirectory: true)
    }

    static func manifestsDirectory() -> URL {
        let url = containerURL().appendingPathComponent("Jobs", isDirectory: true)
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    static func logsDirectory() -> URL {
        let url = containerURL().appendingPathComponent("Logs", isDirectory: true)
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    static func statusURL(for manifestURL: URL) -> URL {
        manifestURL.deletingPathExtension().appendingPathExtension("status.json")
    }
}

struct BrowserCookiePayload: Codable {
    let name: String
    let value: String
    let domain: String
    let path: String
    let secure: Bool
    let httpOnly: Bool?
    let expirationDate: Int?
    let sameSite: String?
}

struct LaunchJobMessage: Codable {
    let sourcePageURL: String
    let courseURL: String
    let host: String
    let selectedLessonIDs: [String]
    let requestedAction: String
    let deleteDownloadedMedia: Bool
    let cookies: [BrowserCookiePayload]
    let course: [String: AnyCodable]
    let outputRoot: String?
    let keepAudio: Bool
    let keepVideo: Bool
    let transcriptSource: String
    let asrBackend: String
    let diarizationMode: String
}

struct JobLessonStatus: Codable, Identifiable {
    let lessonID: String
    let title: String
    let status: String
    let stage: String
    let detail: String?
    let error: String?
    let transcriptFiles: [String]
    let transcriptFolder: String?
    let retainedMediaFiles: [String]

    var id: String { lessonID }

    private enum CodingKeys: String, CodingKey {
        case lessonID
        case title
        case status
        case stage
        case detail
        case error
        case transcriptFiles
        case transcriptFolder
        case retainedMediaFiles
    }

    init(
        lessonID: String,
        title: String,
        status: String,
        stage: String = SWinyDLBridge.pendingStatus,
        detail: String? = nil,
        error: String?,
        transcriptFiles: [String] = [],
        transcriptFolder: String? = nil,
        retainedMediaFiles: [String] = []
    ) {
        self.lessonID = lessonID
        self.title = title
        self.status = status
        self.stage = stage
        self.detail = detail
        self.error = error
        self.transcriptFiles = transcriptFiles
        self.transcriptFolder = transcriptFolder
        self.retainedMediaFiles = retainedMediaFiles
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        lessonID = try container.decode(String.self, forKey: .lessonID)
        title = try container.decode(String.self, forKey: .title)
        status = try container.decode(String.self, forKey: .status)
        stage = try container.decodeIfPresent(String.self, forKey: .stage) ?? status
        detail = try container.decodeIfPresent(String.self, forKey: .detail)
        error = try container.decodeIfPresent(String.self, forKey: .error)
        transcriptFiles = try container.decodeIfPresent([String].self, forKey: .transcriptFiles) ?? []
        transcriptFolder = try container.decodeIfPresent(String.self, forKey: .transcriptFolder)
        retainedMediaFiles = try container.decodeIfPresent([String].self, forKey: .retainedMediaFiles) ?? []
    }
}

struct JobStatusEventPayload: Codable, Identifiable {
    let timestamp: String
    let level: String
    let message: String

    var id: String { "\(timestamp)-\(message)" }
}

struct JobStatusPayload: Codable, Identifiable {
    let jobID: String
    let command: String
    let overallStatus: String
    let courseTitle: String
    let sourcePageURL: String
    let outputRoot: String
    let totalLessons: Int
    let completedLessons: Int
    let startedAt: String?
    let updatedAt: String?
    let elapsedSeconds: Double?
    let activeLessonID: String?
    let activeLessonTitle: String?
    let detail: String?
    let requestedAction: String?
    let diarizationMode: String?
    let deleteDownloadedMedia: Bool?
    let lessons: [JobLessonStatus]
    let events: [JobStatusEventPayload]
    let summaryPath: String?
    let error: String?

    var id: String { jobID }

    private enum CodingKeys: String, CodingKey {
        case jobID
        case command
        case overallStatus
        case courseTitle
        case sourcePageURL
        case outputRoot
        case totalLessons
        case completedLessons
        case startedAt
        case updatedAt
        case elapsedSeconds
        case activeLessonID
        case activeLessonTitle
        case detail
        case requestedAction
        case diarizationMode
        case deleteDownloadedMedia
        case lessons
        case events
        case summaryPath
        case error
    }

    init(
        jobID: String,
        command: String,
        overallStatus: String,
        courseTitle: String,
        sourcePageURL: String,
        outputRoot: String,
        totalLessons: Int,
        completedLessons: Int,
        startedAt: String? = nil,
        updatedAt: String? = nil,
        elapsedSeconds: Double? = nil,
        activeLessonID: String? = nil,
        activeLessonTitle: String? = nil,
        detail: String? = nil,
        requestedAction: String? = nil,
        diarizationMode: String? = nil,
        deleteDownloadedMedia: Bool? = nil,
        lessons: [JobLessonStatus],
        events: [JobStatusEventPayload] = [],
        summaryPath: String? = nil,
        error: String? = nil
    ) {
        self.jobID = jobID
        self.command = command
        self.overallStatus = overallStatus
        self.courseTitle = courseTitle
        self.sourcePageURL = sourcePageURL
        self.outputRoot = outputRoot
        self.totalLessons = totalLessons
        self.completedLessons = completedLessons
        self.startedAt = startedAt
        self.updatedAt = updatedAt
        self.elapsedSeconds = elapsedSeconds
        self.activeLessonID = activeLessonID
        self.activeLessonTitle = activeLessonTitle
        self.detail = detail
        self.requestedAction = requestedAction
        self.diarizationMode = diarizationMode
        self.deleteDownloadedMedia = deleteDownloadedMedia
        self.lessons = lessons
        self.events = events
        self.summaryPath = summaryPath
        self.error = error
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        jobID = try container.decode(String.self, forKey: .jobID)
        command = try container.decode(String.self, forKey: .command)
        overallStatus = try container.decode(String.self, forKey: .overallStatus)
        courseTitle = try container.decode(String.self, forKey: .courseTitle)
        sourcePageURL = try container.decode(String.self, forKey: .sourcePageURL)
        outputRoot = try container.decode(String.self, forKey: .outputRoot)
        totalLessons = try container.decode(Int.self, forKey: .totalLessons)
        completedLessons = try container.decode(Int.self, forKey: .completedLessons)
        startedAt = try container.decodeIfPresent(String.self, forKey: .startedAt)
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt)
        elapsedSeconds = try container.decodeIfPresent(Double.self, forKey: .elapsedSeconds)
        activeLessonID = try container.decodeIfPresent(String.self, forKey: .activeLessonID)
        activeLessonTitle = try container.decodeIfPresent(String.self, forKey: .activeLessonTitle)
        detail = try container.decodeIfPresent(String.self, forKey: .detail)
        requestedAction = try container.decodeIfPresent(String.self, forKey: .requestedAction)
        diarizationMode = try container.decodeIfPresent(String.self, forKey: .diarizationMode)
        deleteDownloadedMedia = try container.decodeIfPresent(Bool.self, forKey: .deleteDownloadedMedia)
        lessons = try container.decodeIfPresent([JobLessonStatus].self, forKey: .lessons) ?? []
        events = try container.decodeIfPresent([JobStatusEventPayload].self, forKey: .events) ?? []
        summaryPath = try container.decodeIfPresent(String.self, forKey: .summaryPath)
        error = try container.decodeIfPresent(String.self, forKey: .error)
    }
}

struct JobEnvelope: Identifiable {
    let manifestURL: URL
    let statusURL: URL
    let status: JobStatusPayload?

    var id: String { manifestURL.lastPathComponent }
}

struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let intValue = try? container.decode(Int.self) {
            value = intValue
        } else if let doubleValue = try? container.decode(Double.self) {
            value = doubleValue
        } else if let boolValue = try? container.decode(Bool.self) {
            value = boolValue
        } else if let stringValue = try? container.decode(String.self) {
            value = stringValue
        } else if let arrayValue = try? container.decode([AnyCodable].self) {
            value = arrayValue.map(\.value)
        } else if let objectValue = try? container.decode([String: AnyCodable].self) {
            value = objectValue.mapValues(\.value)
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case let intValue as Int:
            try container.encode(intValue)
        case let doubleValue as Double:
            try container.encode(doubleValue)
        case let boolValue as Bool:
            try container.encode(boolValue)
        case let stringValue as String:
            try container.encode(stringValue)
        case let arrayValue as [Any]:
            try container.encode(arrayValue.map(AnyCodable.init))
        case let dictionaryValue as [String: Any]:
            try container.encode(dictionaryValue.mapValues(AnyCodable.init))
        default:
            try container.encodeNil()
        }
    }
}

extension JSONEncoder {
    static func bridgeEncoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }
}

extension JSONDecoder {
    static func bridgeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }
}
