import Foundation
import FluidAudio

private struct RunnerOutput: Codable {
    let backend: String
    let modelName: String
    let text: String
    let confidence: Float
    let duration: Double
    let processingTime: Double
    let tokenTimings: [TokenTiming]?
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
    let version: AsrModelVersion

    static func parse(_ argv: [String]) throws -> RunnerArguments {
        var audioPath: String?
        var modelDirectory: String?
        var version = AsrModelVersion.v3
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
            case "--version":
                index += 1
                guard index < argv.count else { throw RunnerError.missingValue(argument) }
                switch argv[index] {
                case "v2":
                    version = .v2
                case "v3":
                    version = .v3
                default:
                    throw RunnerError.invalidValue("Unsupported Parakeet model version: \(argv[index])")
                }
            default:
                throw RunnerError.invalidValue("Unknown argument: \(argument)")
            }
            index += 1
        }

        guard let audioPath else { throw RunnerError.invalidValue("Use --audio <path>.") }
        guard let modelDirectory else { throw RunnerError.invalidValue("Use --model-dir <path>.") }
        return RunnerArguments(audioPath: audioPath, modelDirectory: modelDirectory, version: version)
    }
}

@main
struct ParakeetCoreMLRunner {
    static func main() async {
        do {
            let args = try RunnerArguments.parse(CommandLine.arguments)
            let audioURL = URL(fileURLWithPath: args.audioPath)
            let modelURL = URL(fileURLWithPath: args.modelDirectory, isDirectory: true)

            let models = try await AsrModels.load(
                from: modelURL,
                configuration: AsrModels.defaultConfiguration(),
                version: args.version
            )
            let manager = AsrManager()
            try await manager.loadModels(models)

            var decoderState = TdtDecoderState.make(decoderLayers: models.version.decoderLayers)
            let result = try await manager.transcribe(audioURL, decoderState: &decoderState)

            let payload = RunnerOutput(
                backend: "parakeet-coreml",
                modelName: modelURL.lastPathComponent,
                text: result.text,
                confidence: result.confidence,
                duration: result.duration,
                processingTime: result.processingTime,
                tokenTimings: result.tokenTimings
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
