#if canImport(SwiftData)
import SwiftData

@MainActor
enum DataController {
    static let shared: ModelContainer = {
        do {
            return try ModelContainer(for: WritingProject.self,
                                      Entry.self,
                                      Stage.self)
        } catch {
            print("⚠️ Failed to load ModelContainer: \(error)")
            let config = ModelConfiguration(isStoredInMemoryOnly: true)
            return try! ModelContainer(for: WritingProject.self,
                                      Entry.self,
                                      Stage.self,
                                      configurations: config)
        }
    }()

    static var mainContext: ModelContext {
        shared.mainContext
    }

    static func saveAndNotify(project: WritingProject? = nil) {
        let context = mainContext
        do {
            let previous: Double?
            if let project {
                previous = ProgressAnimationTracker.lastProgress(for: project)
            } else {
                previous = nil
            }

            try context.save()

            if let project {
                let current = project.progress
                if previous == nil || previous != current {
                    NotificationCenter.default.post(name: .projectProgressChanged,
                                                    object: project.id)
                }
            } else {
                let descriptor = FetchDescriptor<WritingProject>()
                if let projects = try? context.fetch(descriptor) {
                    for project in projects {
                        let prev = ProgressAnimationTracker.lastProgress(for: project) ?? -1
                        if prev != project.progress {
                            NotificationCenter.default.post(name: .projectProgressChanged,
                                                            object: project.id)
                        }
                    }
                }
            }
        } catch {
            print("Ошибка сохранения: \(error)")
        }
    }
}
#endif
