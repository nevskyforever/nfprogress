import Foundation
/// Запоминает последний прогресс проектов, чтобы избежать повторного запуска
/// анимации с нуля при изменении данных проекта.
#if canImport(SwiftData)
import SwiftData

@MainActor
enum ProgressAnimationTracker {
    private static var progressMap: [PersistentIdentifier: Double] = [:]
    private static var titleMap: [PersistentIdentifier: String] = [:]
    private static var deadlineMap: [PersistentIdentifier: Date?] = [:]
    private static var goalMap: [PersistentIdentifier: Int] = [:]
    private static var observer: NSObjectProtocol?

    static func lastProgress(for project: WritingProject) -> Double? {
        progressMap[project.id]
    }

    static func setProgress(_ value: Double, for project: WritingProject) {
        progressMap[project.id] = value
    }

    static func lastTitle(for project: WritingProject) -> String? {
        titleMap[project.id]
    }

    static func setTitle(_ value: String, for project: WritingProject) {
        titleMap[project.id] = value
    }

    static func lastDeadline(for project: WritingProject) -> Date? {
        if let value = deadlineMap[project.id] {
            return value
        }
        return nil
    }

    static func setDeadline(_ value: Date?, for project: WritingProject) {
        deadlineMap[project.id] = value
    }

    static func lastGoal(for project: WritingProject) -> Int? {
        goalMap[project.id]
    }

    static func setGoal(_ value: Int, for project: WritingProject) {
        goalMap[project.id] = value
    }

    static func updateAttributes(for project: WritingProject) {
        setTitle(project.title, for: project)
        setDeadline(project.deadline, for: project)
        setGoal(project.goal, for: project)
    }

    /// Подготавливает трекер, сбрасывая стартовый прогресс до нуля и
    /// подписываясь на уведомления об изменении прогресса.
    static func initialize(with projects: [WritingProject]) {
        if progressMap.isEmpty {
            projects.forEach {
                setProgress(0, for: $0)
            }
        }
        projects.forEach { updateAttributes(for: $0) }
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
