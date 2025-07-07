#if canImport(SwiftData)
import Foundation
import SwiftData

@Model
class WritingProject {
    var title: String
    var goal: Int
    var deadline: Date?
    var entries: [Entry]
    var stages: [Stage]
    /// Порядок отображения проектов в списке
    var order: Int = 0
    /// Состояние графика: `true` если график свернут
    var isChartCollapsed: Bool = false
    /// Тип синхронизации документа
    var syncType: SyncDocumentType?
    /// Путь к файлу Word для синхронизации
    var wordFilePath: String?
    /// Bookmark для доступа к файлу Word
    var wordFileBookmark: Data?
    /// Путь к проекту Scrivener
    var scrivenerProjectPath: String?
    /// Bookmark для доступа к проекту Scrivener
    var scrivenerProjectBookmark: Data?
    /// Выбранный ID элемента Scrivener
    var scrivenerItemID: String?
    /// Название выбранного элемента Scrivener
    var scrivenerItemTitle: String?
    /// Приостановлена ли синхронизация
    var syncPaused: Bool = false
    /// Количество символов в файле при последней проверке
    var lastWordCharacters: Int?
    var lastScrivenerCharacters: Int?
    /// Дата последнего изменения файла Word
    var lastWordModified: Date?
    var lastScrivenerModified: Date?
    /// Прогресс в момент последнего шеринга
    var lastShareProgress: Int?

    init(title: String, goal: Int, deadline: Date? = nil, order: Int = 0, isChartCollapsed: Bool = false) {
        self.title = title
        self.goal = goal
        self.deadline = deadline
        self.entries = []
        self.stages = []
        self.order = order
        self.isChartCollapsed = isChartCollapsed
        self.scrivenerItemTitle = nil
        self.syncPaused = false
    }

    /// Все записи проекта и этапов без повторов
    private var allEntries: [Entry] {
        var seen = Set<UUID>()
        let combined = entries + stages.flatMap { $0.entries }
        return combined.filter { seen.insert($0.id).inserted }
    }

    var sortedEntries: [Entry] {
        allEntries.sorted { $0.date < $1.date }
    }

    func stageForEntry(_ entry: Entry) -> Stage? {
        for stage in stages {
            if stage.entries.contains(where: { $0.id == entry.id }) {
                return stage
            }
        }
        return nil
    }

    func globalProgress(for entry: Entry) -> Int {
        let entries = sortedEntries
        guard let index = entries.firstIndex(where: { $0.id == entry.id }) else { return 0 }
        let progress = entries.prefix(index + 1).cumulativeProgress()
        return progress
    }

    func previousGlobalProgress(before entry: Entry) -> Int {
        let entries = sortedEntries
        guard let idx = entries.firstIndex(where: { $0.id == entry.id }) else { return 0 }
        if idx == 0 { return 0 }
        let prev = entries[idx - 1]
        return globalProgress(for: prev)
    }

    var currentProgress: Int {
        let total = sortedEntries.cumulativeProgress()
        return max(0, total)
    }

    var previousProgress: Int {
        guard sortedEntries.count >= 2 else { return 0 }
        let prevEntries = sortedEntries.dropLast()
        return prevEntries.cumulativeProgress()
    }

    /// Сумма символов по всем этапам
    var totalStageCharacters: Int {
        stages.reduce(0) { $0 + $1.sortedEntries.cumulativeProgress() }
    }

    /// Общий прогресс проекта в диапазоне 0...1
    var progress: Double {
        guard goal > 0 else { return 0 }
        return min(Double(currentProgress) / Double(goal), 1.0)
    }

    var progressPercentage: Double {
        progress
    }

    var changeSinceLast: Int {
        currentProgress - previousProgress
    }

    private var languageIdentifier: String {
        let defaultLang = AppLanguage.systemDefault.rawValue
        let raw = UserDefaults.standard.string(forKey: "language") ?? defaultLang
        let lang = AppLanguage(rawValue: raw) ?? AppLanguage.systemDefault
        return lang.resolvedIdentifier
    }

    private func localized(_ key: String) -> String {
        if let path = Bundle.main.path(forResource: languageIdentifier, ofType: "lproj"),
           let bundle = Bundle(path: path) {
            return bundle.localizedString(forKey: key, value: nil, table: nil)
        }
        return NSLocalizedString(key, comment: "")
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
            return String(format: localized("motivation_positive"), changeSinceLast)
        } else if changeSinceLast < 0 {
            return localized("motivation_negative")
        } else {
            return nil
        }
    }


    var streak: Int {
       let calendar = Calendar.current
       let entriesByDay = Dictionary(grouping: sortedEntries) { calendar.startOfDay(for: $0.date) }
       let entryDays = entriesByDay.keys.sorted()

        guard !entryDays.isEmpty else { return 0 }
        // Подсчет серии ведётся только при наличии записи за сегодня
        let today = calendar.startOfDay(for: Date())
        guard entryDays.contains(today) else { return 0 }

        func progress(atEndOf day: Date) -> Int {
            guard let entries = entriesByDay[day] else { return 0 }
            let last = entries.max(by: { $0.date < $1.date })!
            return globalProgress(for: last)
        }

        // Формируем список всех дней между первой и последней записью
        var allDays: [Date] = []
        var day = calendar.startOfDay(for: entryDays.first!)
        let lastDay = calendar.startOfDay(for: entryDays.last!)
        while day <= lastDay {
            allDays.append(day)
            day = calendar.date(byAdding: .day, value: 1, to: day)!
        }

        // Вычисляем прогресс на конец дня, перенося предыдущее значение при отсутствии записей
        var progressByDay: [Date: Int] = [:]
        var lastProgress = 0
        for day in allDays {
            if entryDays.contains(day) {
                lastProgress = progress(atEndOf: day)
            }
            progressByDay[day] = lastProgress
        }

        // Считаем серию, проверяя последовательные дни от последнего к первому
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

    /// Есть ли запись за текущий день
    private var hasEntryToday: Bool {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        return sortedEntries.contains { calendar.isDate($0.date, inSameDayAs: today) }
    }

    /// Подсказка продолжить серию, если запись за сегодня отсутствует
    var streakPrompt: String? {
        guard deadline != nil else { return nil }
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        let uniqueDays = Array(Set(
            sortedEntries.map { calendar.startOfDay(for: $0.date) }
        )).sorted()

        if hasEntryToday {
            return nil
        }

        guard let last = uniqueDays.last else {
            return localized("streak_start")
        }

        let yesterday = calendar.date(byAdding: .day, value: -1, to: today)!
        if calendar.isDate(last, inSameDayAs: yesterday), streak > 0 {
            return String(format: localized("streak_continue"), streak)
        }
        return localized("streak_start")
    }

    /// Текстовое описание текущей серии
    var streakStatus: String {
        guard deadline != nil else { return "" }
        if streak == 0 {
            return localized("streak_start")
        } else {
            return String(format: localized("streak_success"), streak)
        }
    }

    var progressLastWeek: Int {
        let calendar = Calendar.current
        guard let weekAgo = calendar.date(byAdding: .day, value: -7, to: .now) else { return 0 }
        let entriesLastWeek = sortedEntries.filter { $0.date >= weekAgo }
        guard let first = entriesLastWeek.first, let last = entriesLastWeek.last else { return 0 }
        let start = globalProgress(for: first)
        let end = globalProgress(for: last)
        return end - start
    }

    var progressLastWeekPercent: Int {
        guard goal > 0 else { return 0 }
        return Int(Double(progressLastWeek) / Double(goal) * 100)
    }

    /// Количество символов, изменённых сегодня во всех записях проекта
    var charactersWrittenToday: Int {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        let todayEntries = sortedEntries.filter { calendar.isDate($0.date, inSameDayAs: today) }
        var total = 0
        for entry in todayEntries {
            let current = globalProgress(for: entry)
            let previous = previousGlobalProgress(before: entry)
            total += current - previous
        }
        return total
    }

    /// Соответствие ``Identifiable`` и ``Hashable`` позволяет
    /// использовать ``WritingProject`` в навигации.
}

extension WritingProject: Identifiable, Hashable {
    static func == (lhs: WritingProject, rhs: WritingProject) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}

@Model
class Entry: Identifiable {
    var id = UUID()
    var date: Date
    var characterCount: Int
    /// Источник синхронизации
    var syncSource: SyncDocumentType?

    init(date: Date, characterCount: Int) {
        self.date = date
        self.characterCount = characterCount
    }
}

extension Sequence where Element == WritingProject {
    /// Суммарное количество символов, написанных сегодня во всех проектах
    func charactersWrittenToday() -> Int {
        self.reduce(0) { $0 + $1.charactersWrittenToday }
    }
}

#endif
