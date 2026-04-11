// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ParakeetCoreMLRunner",
    platforms: [
        .macOS(.v14),
    ],
    products: [
        .executable(
            name: "parakeet-coreml-runner",
            targets: ["ParakeetCoreMLRunner"]
        ),
        .executable(
            name: "speaker-diarizer-coreml-runner",
            targets: ["SpeakerDiarizerCoreMLRunner"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/FluidInference/FluidAudio.git", branch: "main"),
    ],
    targets: [
        .executableTarget(
            name: "ParakeetCoreMLRunner",
            dependencies: [
                .product(name: "FluidAudio", package: "FluidAudio"),
            ]
        ),
        .executableTarget(
            name: "SpeakerDiarizerCoreMLRunner",
            dependencies: [
                .product(name: "FluidAudio", package: "FluidAudio"),
            ]
        ),
    ]
)
