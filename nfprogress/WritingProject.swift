import Foundation
import SwiftData

@Model
class WritingProject {
    var title: String
    var goal: Int
    var deadline: Date?
    var entries: [Entry]

    init(title: String, goal: Int, deadline: Date? = nil) {
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
        let entriesByDay = Dictionary(grouping: sortedEntries) { calendar.startOfDay(for: $0.date) }
        let days = entriesByDay.keys.sorted()

        guard !days.isEmpty else { return 0 }

        func progress(atEndOf day: Date) -> Int {
            entriesByDay[day]!.max(by: { $0.date < $1.date })!.characterCount
        }

        // If нет дедлайна, считаем подряд дни с любыми записями
        guard let deadline else {
            var streakCount = 1
            var current = days.last!
            while days.contains(calendar.date(byAdding: .day, value: -streakCount, to: current)!) {
                streakCount += 1
            }
            return streakCount
        }

        var streakCount = 0
        for index in stride(from: days.count - 1, through: 0, by: -1) {
            let day = days[index]
            let endProgress = progress(atEndOf: day)
            let startProgress = index > 0 ? progress(atEndOf: days[index - 1]) : 0
            let delta = endProgress - startProgress
            let daysLeft = calendar.dateComponents([.day], from: day, to: deadline).day ?? 0
            guard daysLeft > 0 else { break }
            let target = max(0, (goal - startProgress) / daysLeft)
            if delta >= target {
                streakCount += 1
            } else {
                break
            }
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

