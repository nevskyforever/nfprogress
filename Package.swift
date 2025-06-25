// swift-tools-version: 6.1
import PackageDescription

let package = Package(
    name: "nfprogress",
    defaultLocalization: "ru",
    platforms: [
        .macOS(.v14),
        .iOS(.v17)
    ],
    products: [
        .executable(
            name: "nfprogress",
            targets: ["nfprogress"]
        ),
    ],
    targets: [
        .executableTarget(
            name: "nfprogress",
            path: "nfprogress",
            resources: [
                .process("Resources")
            ]
        ),
        .testTarget(
            name: "nfprogressTests",
            dependencies: ["nfprogress"],
            path: "nfprogressTests"
        )
    ]
)

// test auto-merge
