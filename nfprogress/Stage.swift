#if canImport(SwiftData)
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

    /// Записи этого этапа без повторов
    private var uniqueEntries: [Entry] {
        var seen = Set<UUID>()
        return entries.filter { seen.insert($0.id).inserted }
    }

    var sortedEntries: [Entry] {
        uniqueEntries.sorted { $0.date < $1.date }
    }

    var currentProgress: Int {
        max(0, uniqueEntries.reduce(0) { $0 + $1.characterCount })
    }

    var progressPercentage: Double {
        guard goal > 0 else { return 0 }
        let percent = Double(currentProgress) / Double(goal)
        return min(max(percent, 0), 1.0)
    }
}
#endif
