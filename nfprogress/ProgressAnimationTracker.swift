import Foundation
/// Запоминает последний прогресс проектов, чтобы избежать повторного запуска
/// анимации с нуля при изменении данных проекта.
#if canImport(SwiftData)
import SwiftData

@MainActor
enum ProgressAnimationTracker {
    private static var progressMap: [PersistentIdentifier: Double] = [:]
    private static var observer: NSObjectProtocol?

    static func lastProgress(for project: WritingProject) -> Double? {
        progressMap[project.id]
    }

    static func setProgress(_ value: Double, for project: WritingProject) {
        progressMap[project.id] = value
    }

    /// Сохраняет прогресс всех проектов и подписывается на его изменения.
    static func initialize(with projects: [WritingProject]) {
        projects.forEach { setProgress($0.progress, for: $0) }
        guard observer == nil else { return }
        observer = NotificationCenter.default.addObserver(forName: .projectProgressChanged,
                                                         object: nil,
                                                         queue: .main) { note in
            guard let id = note.object as? PersistentIdentifier else { return }
            let descriptor = FetchDescriptor<WritingProject>(predicate: #Predicate { $0.id == id })
            if let project = try? DataController.mainContext.fetch(descriptor).first {
                setProgress(project.progress, for: project)
            }
        }
    }
}
#endif
