import Foundation
/// Запоминает последний прогресс проектов, чтобы избежать повторного запуска
/// анимации с нуля при изменении данных проекта.
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
