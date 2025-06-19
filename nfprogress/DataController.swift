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
}
