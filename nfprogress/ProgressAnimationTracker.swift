import Foundation
#if canImport(SwiftData)
import SwiftData

@MainActor
enum ProgressAnimationTracker {
    private static var progressMap: [PersistentIdentifier: Double] = [:]

    static func lastProgress(for project: WritingProject) -> Double? {
        progressMap[project.id]
    }

    static func setProgress(_ value: Double, for project: WritingProject) {
        progressMap[project.id] = value
    }
}
#endif
