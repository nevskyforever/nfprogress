import Foundation
import SwiftData

@Model
class Stage: Identifiable {
    var id: UUID
    var title: String
    var goal: Int
    var entries: [Entry] = []

    init(id: UUID = UUID(), title: String, goal: Int) {
        self.id = id
        self.title = title
        self.goal = goal
    }

    @Transient
    var sortedEntries: [Entry] {
        entries.sorted { $0.date < $1.date }
    }

    @Transient
    var currentProgress: Int {
        sortedEntries.last?.characterCount ?? 0
    }
}
