import Foundation
import SwiftData

@Model
class WritingProject {
    var title: String
    var goal: Int
    var deadline: Date?
    var entries: [Entry]
    var isStage: Bool
    @Relationship(deleteRule: .cascade, inverse: \WritingProject.parent)
    var stages: [WritingProject]
    var parent: WritingProject?

    init(title: String, goal: Int, deadline: Date? = nil, isStage: Bool = false, parent: WritingProject? = nil) {
        self.title = title
        self.goal = goal
        self.deadline = deadline
        self.entries = []
        self.isStage = isStage
        self.stages = []
        self.parent = parent
    }

    /// Entries of this project only, sorted by date
    var ownSortedEntries: [Entry] {
        entries.sorted { $0.date < $1.date }
    }

    /// All entries including stages if this is a parent project
    var sortedEntries: [Entry] {
        if isStage {
            return ownSortedEntries
        }

        let stageEntries = stages.flatMap { $0.sortedEntries }
        return (entries + stageEntries).sorted { $0.date < $1.date }
    }

    /// Progress for this project including its stages
    var currentProgress: Int {
        if isStage {
            return ownSortedEntries.last?.characterCount ?? 0
        }

        let own = ownSortedEntries.last?.characterCount ?? 0
        let stageTotal = stages.reduce(0) { $0 + $1.currentProgress }
        return own + stageTotal
    }

    var previousProgress: Int {
        if isStage {
            guard ownSortedEntries.count >= 2 else { return 0 }
            return ownSortedEntries[ownSortedEntries.count - 2].characterCount
        }

        let ownPrev = ownSortedEntries.count >= 2 ? ownSortedEntries[ownSortedEntries.count - 2].characterCount : 0
        let stagePrev = stages.reduce(0) { $0 + $1.previousProgress }
        return ownPrev + stagePrev
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

    var motivationalMessage: String? {
        if changeSinceLast > 0 {
            return "👍 Прогресс: +\(changeSinceLast) символов"
        } else if changeSinceLast < 0 {
            return "⚠️ Меньше, чем в прошлый раз"
        } else {
            return nil
        }
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

    var progressLastWeek: Int {
        let calendar = Calendar.current
        guard let weekAgo = calendar.date(byAdding: .day, value: -7, to: .now) else { return 0 }
        let entriesLastWeek = sortedEntries.filter { $0.date >= weekAgo }
        guard let first = entriesLastWeek.first, let last = entriesLastWeek.last else { return 0 }
        return last.characterCount - first.characterCount
    }

    var progressLastWeekPercent: Int {
        guard goal > 0 else { return 0 }
        return Int(Double(progressLastWeek) / Double(goal) * 100)
    }
}

@Model
class Entry: Identifiable {
    var id = UUID()
    var date: Date
    var characterCount: Int

    init(date: Date, characterCount: Int) {
        self.date = date
        self.characterCount = characterCount
    }
}

