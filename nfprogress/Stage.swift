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
        guard let last = sortedEntries.last else { return 0 }
        return max(0, last.characterCount - startProgress)
    }

    var progressPercentage: Double {
        guard goal > 0 else { return 0 }
        return Double(currentProgress) / Double(goal)
    }
}

extension Stage {
    /// Calculate progress based only on this stage's entries within the given project
    func currentProgress(in project: WritingProject) -> Int {
        let sorted = project.sortedEntries
        let ids = Set(entries.map { $0.id })
        var last = startProgress
        var total = 0
        for entry in sorted {
            if entry.characterCount < startProgress {
                last = entry.characterCount
                continue
            }
            if ids.contains(entry.id) {
                total += entry.characterCount - last
            }
            last = entry.characterCount
        }
        return max(0, total)
    }

    /// Percentage progress relative to this stage's goal within the given project
    func progressPercentage(in project: WritingProject) -> Double {
        guard goal > 0 else { return 0 }
        return Double(currentProgress(in: project)) / Double(goal)
    }
}
