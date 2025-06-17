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

    /// True if there is already an entry for the current day
    private var hasEntryToday: Bool {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        return sortedEntries.contains { calendar.isDate($0.date, inSameDayAs: today) }
    }

    /// Prompt encouraging to keep the streak if today's entry is missing
    var streakPrompt: String? {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        let uniqueDays = Array(Set(
            sortedEntries.map { calendar.startOfDay(for: $0.date) }
        )).sorted()

        if hasEntryToday {
            return nil
        }

        guard let last = uniqueDays.last else {
            return "Начнем путь к цели?"
        }

        let yesterday = calendar.date(byAdding: .day, value: -1, to: today)!
        if calendar.isDate(last, inSameDayAs: yesterday) {
            return "Вы в ударе \(streak) дней подряд, продолжим?"
        }

        return "Начнем путь к цели?"
    }

    /// Text describing the current streak state
    var streakDescription: String {
        if streak == 0 {
            return "Начнем путь к цели?"
        } else {
            return "🔥 В цели \(streak) дней подряд"
        }
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

