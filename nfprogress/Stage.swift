import Foundation
import SwiftData

@Model
class Stage: Identifiable {
    var id = UUID()
    var title: String
    var goal: Int
    var deadline: Date?
    var startProgress: Int
    var entries: [Entry]

    init(title: String, goal: Int, deadline: Date? = nil, startProgress: Int) {
        self.title = title
        self.goal = goal
        self.deadline = deadline
        self.startProgress = startProgress
        self.entries = []
    }

    var sortedEntries: [Entry] {
        entries.sorted { $0.date < $1.date }
    }

    var currentProgress: Int {
        entries.reduce(0) { $0 + $1.characterCount }
    }

    var progressPercentage: Double {
        guard goal > 0 else { return 0 }
        return min(Double(currentProgress) / Double(goal), 1.0)
    }
}
