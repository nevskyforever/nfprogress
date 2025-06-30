import Foundation
#if canImport(SwiftData)
import SwiftData

@MainActor
enum ProgressAnimationTracker {
    private static var progressMap: [ObjectIdentifier: Double] = [:]

    static func lastProgress(for project: WritingProject) -> Double? {
        progressMap[ObjectIdentifier(project)]
    }

    static func setProgress(_ value: Double, for project: WritingProject) {
        progressMap[ObjectIdentifier(project)] = value
    }
}
#endif
