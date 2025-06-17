import SwiftData

@MainActor
enum DataController {
    static let shared: ModelContainer = {
        do {
            return try ModelContainer(for: WritingProject.self, Stage.self, Entry.self)
        } catch {
            assertionFailure("SwiftData init failed: \(error)")
            let config = ModelConfiguration(isStoredInMemoryOnly: true)
            return try! ModelContainer(for: WritingProject.self, Stage.self, Entry.self,
                                      configurations: config)
        }
    }()
}
