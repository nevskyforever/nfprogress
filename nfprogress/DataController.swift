import SwiftData

@MainActor
enum DataController {
    static let shared: ModelContainer = {
        do {
            return try ModelContainer(for: WritingProject.self, Entry.self)
        } catch {
            print("Failed to load model container: \(error.localizedDescription)")
            let config = ModelConfiguration(isStoredInMemory: true)
            return (try? ModelContainer(for: WritingProject.self, Entry.self, configurations: config))!
        }
    }()
}
