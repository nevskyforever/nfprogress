import Foundation
import SwiftData

@Model
class WritingProject {
    var title: String
    var goal: Int
    var deadline: Date?
    var entries: [Entry]
    var stages: [Stage]
    var areStagesExpanded: Bool

    init(title: String, goal: Int, deadline: Date? = nil) {
        self.title = title
        self.goal = goal
        self.deadline = deadline
        self.entries = []
        self.stages = []
        self.areStagesExpanded = true
    }

    @Transient
    var sortedEntries: [Entry] {
        entries.sorted { $0.date < $1.date }
    }

    @Transient
    var allEntries: [Entry] {
        let stageEntries = stages.flatMap { $0.entries }
        return (entries + stageEntries).sorted { $0.date < $1.date }
    }

    @Transient
    var currentProgress: Int {
        allEntries.last?.characterCount ?? 0
    }

    @Transient
    var previousProgress: Int {
        guard allEntries.count >= 2 else { return 0 }
        return allEntries[allEntries.count - 2].characterCount
    }

    @Transient
    var totalSymbolCount: Int {
        (entries + stages.flatMap { $0.entries }).reduce(0) { $0 + $1.characterCount }
    }

    @Transient
    var progressPercentage: Double {
        guard goal > 0 else { return 0 }
        return Double(totalSymbolCount) / Double(goal)
    }

    @Transient
    var changeSinceLast: Int {
        currentProgress - previousProgress
    }

    @Transient
    var daysLeft: Int {
        guard let deadline else { return 0 }
        let calendar = Calendar.current
        return calendar.dateComponents([.day], from: .now, to: deadline).day ?? 0
    }

    @Transient
    var dailyTarget: Int? {
        guard daysLeft > 0 else { return nil }
        return max(0, (goal - totalSymbolCount) / daysLeft)
    }

    @Transient
    var motivationalMessage: String? {
        if changeSinceLast > 0 {
            return "👍 Прогресс: +\(changeSinceLast) символов"
        } else if changeSinceLast < 0 {
            return "⚠️ Меньше, чем в прошлый раз"
        } else {
            return nil
        }
    }


    @Transient
    var streak: Int {
       let calendar = Calendar.current
       let entriesByDay = Dictionary(grouping: allEntries) { calendar.startOfDay(for: $0.date) }
       let entryDays = entriesByDay.keys.sorted()

        guard !entryDays.isEmpty else { return 0 }
        // Streak counts only when there is an entry for today
        let today = calendar.startOfDay(for: Date())
        guard entryDays.contains(today) else { return 0 }

        func progress(atEndOf day: Date) -> Int {
            guard let entries = entriesByDay[day] else { return 0 }
            return entries.max(by: { $0.date < $1.date })!.characterCount
        }

        // Build list of all days between first and last entry
        var allDays: [Date] = []
        var day = calendar.startOfDay(for: entryDays.first!)
        let lastDay = calendar.startOfDay(for: entryDays.last!)
        while day <= lastDay {
            allDays.append(day)
            day = calendar.date(byAdding: .day, value: 1, to: day)!
        }

        // Compute progress at end of each day, carrying forward progress when there are no entries
        var progressByDay: [Date: Int] = [:]
        var lastProgress = 0
        for day in allDays {
            if entryDays.contains(day) {
                lastProgress = progress(atEndOf: day)
            }
            progressByDay[day] = lastProgress
        }

        // Calculate streak by checking consecutive calendar days from the last day backwards
        var streakCount = 0
        for index in stride(from: allDays.count - 1, through: 0, by: -1) {
            let day = allDays[index]
            let endProgress = progressByDay[day] ?? 0
            let startProgress = index > 0 ? (progressByDay[allDays[index - 1]] ?? 0) : 0
            let delta = endProgress - startProgress

            if let deadline {
                let daysLeft = calendar.dateComponents([.day], from: day, to: deadline).day ?? 0
                guard daysLeft > 0 else { break }
                let target = max(0, (goal - startProgress) / daysLeft)
                if delta >= target {
                    streakCount += 1
                } else {
                    break
                }
            } else {
                if delta > 0 {
                    streakCount += 1
                } else {
                    break
                }
            }
        }
        return streakCount
    }

    /// True if there is already an entry for the current day
    @Transient
    private var hasEntryToday: Bool {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        return allEntries.contains { calendar.isDate($0.date, inSameDayAs: today) }
    }

    /// Prompt encouraging to keep the streak if today's entry is missing
    @Transient
    var streakPrompt: String? {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        let uniqueDays = Array(Set(
            allEntries.map { calendar.startOfDay(for: $0.date) }
        )).sorted()

        if hasEntryToday {
            return nil
        }

        guard let last = uniqueDays.last else {
            return "Начнем путь к цели?"
        }

        let yesterday = calendar.date(byAdding: .day, value: -1, to: today)!
        if calendar.isDate(last, inSameDayAs: yesterday), streak > 0 {
            return "Вы в ударе \(streak) дней подряд, продолжим?"
        }

        return "Начнем путь к цели?"
    }

    /// Text describing the current streak state
    @Transient
    var streakStatus: String {
        if streak == 0 {
            return "Начнем путь к цели?"
        } else {
            return "🔥 В цели \(streak) дней подряд"
        }
    }

    @Transient
    var progressLastWeek: Int {
        let calendar = Calendar.current
        guard let weekAgo = calendar.date(byAdding: .day, value: -7, to: .now) else { return 0 }
        let entriesLastWeek = allEntries.filter { $0.date >= weekAgo }
        guard let first = entriesLastWeek.first, let last = entriesLastWeek.last else { return 0 }
        return last.characterCount - first.characterCount
    }

    @Transient
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
    var stage: Stage?

    init(date: Date, characterCount: Int, stage: Stage? = nil) {
        self.date = date
        self.characterCount = characterCount
        self.stage = stage
    }
}

