// swift-tools-version: 6.1
import PackageDescription

let package = Package(
    name: "nfprogress",
    platforms: [
        .macOS(.v14)
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
            path: "nfprogress"
        ),
        .testTarget(
            name: "nfprogressTests",
            dependencies: ["nfprogress"],
            path: "nfprogressTests"
        )
    ]
)
