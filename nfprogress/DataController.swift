import SwiftData

@MainActor
enum DataController {
    static let shared: ModelContainer = {
        do {
            return try ModelContainer(for: WritingProject.self, Stage.self, Entry.self)
        } catch {
            print("ModelContainer initialization error:", error)
            fatalError("Failed to initialize SwiftData container: \(error)")
        }
    }()
}
