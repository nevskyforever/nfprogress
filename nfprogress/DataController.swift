import SwiftData

@MainActor
enum DataController {
    static let shared: ModelContainer = {
        do {
            return try ModelContainer(for: WritingProject.self, Entry.self)
        } catch {
            print("Failed to create ModelContainer: \(error)")
            let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
            return try! ModelContainer(for: WritingProject.self, Entry.self, configurations: configuration)
        }
    }()
}
