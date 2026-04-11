import FluidAudio
import Foundation

private struct RunnerSegment: Codable {
    let speakerId: String
    let startTime: Float
    let endTime: Float
    let qualityScore: Float
}

private struct RunnerOutput: Codable {
    let backend: String
    let modelName: String
    let segments: [RunnerSegment]
}

private enum RunnerError: LocalizedError {
    case missingValue(String)
    case invalidValue(String)

    var errorDescription: String? {
        switch self {
        case .missingValue(let flag):
            return "Missing value for \(flag)"
        case .invalidValue(let message):
            return message
        }
    }
}

private struct RunnerArguments {
    let audioPath: String
    let modelDirectory: String

    static func parse(_ argv: [String]) throws -> RunnerArguments {
        var audioPath: String?
        var modelDirectory: String?
        var index = 1

        while index < argv.count {
            let argument = argv[index]
            switch argument {
            case "--audio":
                index += 1
                guard index < argv.count else { throw RunnerError.missingValue(argument) }
                audioPath = argv[index]
            case "--model-dir":
                index += 1
                guard index < argv.count else { throw RunnerError.missingValue(argument) }
                modelDirectory = argv[index]
            default:
                throw RunnerError.invalidValue("Unknown argument: \(argument)")
            }
            index += 1
        }

        guard let audioPath else { throw RunnerError.invalidValue("Use --audio <path>.") }
        guard let modelDirectory else { throw RunnerError.invalidValue("Use --model-dir <path>.") }
        return RunnerArguments(audioPath: audioPath, modelDirectory: modelDirectory)
    }
}

private enum RunnerDefaults {
    static let clusteringThreshold = 0.45
    static let minSpeakers = 1
    static let maxSpeakers = 4
    static let minSegmentDurationSeconds = 0.6
    static let minGapDurationSeconds = 0.2
    static let segmentationMinDurationOn = 0.2
    static let segmentationMinDurationOff = 0.15
}

private func envDouble(_ name: String, default defaultValue: Double) -> Double {
    guard let raw = ProcessInfo.processInfo.environment[name], let value = Double(raw) else {
        return defaultValue
    }
    return value
}

private func envInt(_ name: String, default defaultValue: Int) -> Int {
    guard let raw = ProcessInfo.processInfo.environment[name], let value = Int(raw) else {
        return defaultValue
    }
    return value
}

@main
struct SpeakerDiarizerCoreMLRunner {
    static func main() async {
        do {
            let args = try RunnerArguments.parse(CommandLine.arguments)
            let modelURL = URL(fileURLWithPath: args.modelDirectory, isDirectory: true)
            let models = try await OfflineDiarizerModels.load(from: modelURL)
            var config = OfflineDiarizerConfig.default
            config.clustering.threshold = envDouble(
                "ECHO360_DIARIZER_CLUSTERING_THRESHOLD",
                default: RunnerDefaults.clusteringThreshold
            )
            config.clustering.minSpeakers = envInt(
                "ECHO360_DIARIZER_MIN_SPEAKERS",
                default: RunnerDefaults.minSpeakers
            )
            config.clustering.maxSpeakers = envInt(
                "ECHO360_DIARIZER_MAX_SPEAKERS",
                default: RunnerDefaults.maxSpeakers
            )
            config.embedding.minSegmentDurationSeconds = envDouble(
                "ECHO360_DIARIZER_MIN_SEGMENT_DURATION",
                default: RunnerDefaults.minSegmentDurationSeconds
            )
            config.postProcessing.minGapDurationSeconds = envDouble(
                "ECHO360_DIARIZER_MIN_GAP_DURATION",
                default: RunnerDefaults.minGapDurationSeconds
            )
            config.segmentation.minDurationOn = envDouble(
                "ECHO360_DIARIZER_SEGMENTATION_MIN_ON",
                default: RunnerDefaults.segmentationMinDurationOn
            )
            config.segmentation.minDurationOff = envDouble(
                "ECHO360_DIARIZER_SEGMENTATION_MIN_OFF",
                default: RunnerDefaults.segmentationMinDurationOff
            )
            let manager = OfflineDiarizerManager(config: config)
            manager.initialize(models: models)
            let audioURL = URL(fileURLWithPath: args.audioPath)
            let result = try await manager.process(audioURL)

            let payload = RunnerOutput(
                backend: "speaker-diarizer-coreml-offline",
                modelName: modelURL.lastPathComponent,
                segments: result.segments.map { segment in
                    RunnerSegment(
                        speakerId: segment.speakerId,
                        startTime: segment.startTimeSeconds,
                        endTime: segment.endTimeSeconds,
                        qualityScore: segment.qualityScore
                    )
                }
            )
            let data = try JSONEncoder().encode(payload)
            FileHandle.standardOutput.write(data)
        } catch {
            let message = error.localizedDescription.isEmpty ? String(describing: error) : error.localizedDescription
            FileHandle.standardError.write(Data((message + "\n").utf8))
            Foundation.exit(2)
        }
    }
}
