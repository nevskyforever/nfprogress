import Foundation
import SwiftData

@Model
class Stage: Identifiable {
    var id: UUID
    var title: String
    var goal: Int
    var deadline: Date?
    var entries: [Entry]

    init(id: UUID = UUID(), title: String, goal: Int, deadline: Date? = nil) {
        self.id = id
        self.title = title
        self.goal = goal
        self.deadline = deadline
        self.entries = []
    }

    var sortedEntries: [Entry] {
        entries.sorted { $0.date < $1.date }
    }

    var currentProgress: Int {
        sortedEntries.last?.characterCount ?? 0
    }

    var previousProgress: Int {
        guard sortedEntries.count >= 2 else { return 0 }
        return sortedEntries[sortedEntries.count - 2].characterCount
    }

    var progressPercentage: Double {
        guard goal > 0 else { return 0 }
        return Double(currentProgress) / Double(goal)
    }

    var changeSinceLast: Int {
        currentProgress - previousProgress
    }

    var daysLeft: Int {
        guard let deadline else { return 0 }
        let calendar = Calendar.current
        return calendar.dateComponents([.day], from: .now, to: deadline).day ?? 0
    }

    var dailyTarget: Int? {
        guard daysLeft > 0 else { return nil }
        return max(0, (goal - currentProgress) / daysLeft)
    }

    var streak: Int {
        let calendar = Calendar.current
        let uniqueDays = Array(Set(
            sortedEntries.map { calendar.startOfDay(for: $0.date) }
        )).sorted()
        guard let last = uniqueDays.last else { return 0 }
        var streakCount = 1
        var current = last
        while uniqueDays.contains(calendar.date(byAdding: .day, value: -streakCount, to: current)!) {
            streakCount += 1
        }
        return streakCount
    }
}
