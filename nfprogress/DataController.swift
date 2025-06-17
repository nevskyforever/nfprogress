import SwiftData

@MainActor
enum DataController {
    static let shared: ModelContainer = {
        try! ModelContainer(for: WritingProject.self, Stage.self, Entry.self)
    }()
}
