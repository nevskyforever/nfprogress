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
    /// Порядок этапа в списке
    var order: Int = 0
    var entries: [Entry]
    /// Тип синхронизации документа для этапа
    var syncType: SyncDocumentType?
    /// Путь к файлу Word
    var wordFilePath: String?
    /// Bookmark для доступа к файлу Word
    var wordFileBookmark: Data?
    /// Путь к проекту Scrivener
    var scrivenerProjectPath: String?
    /// Bookmark для доступа к проекту Scrivener
    var scrivenerProjectBookmark: Data?
    /// ID выбранного элемента Scrivener
    var scrivenerItemID: String?
    /// Название выбранного элемента Scrivener
    var scrivenerItemTitle: String?
    /// Последнее известное количество символов в Word
    var lastWordCharacters: Int?
    /// Последняя дата изменения Word
    var lastWordModified: Date?
    /// Последнее известное количество символов в Scrivener
    var lastScrivenerCharacters: Int?
    /// Последняя дата изменения Scrivener
    var lastScrivenerModified: Date?
    /// Приостановлена ли синхронизация
    var syncPaused: Bool = false

    init(title: String, goal: Int, deadline: Date? = nil, startProgress: Int, order: Int = 0) {
        self.title = title
        self.goal = goal
        self.deadline = deadline
        self.startProgress = startProgress
        self.order = order
        self.entries = []
        self.syncType = nil
        self.wordFilePath = nil
        self.wordFileBookmark = nil
        self.scrivenerProjectPath = nil
        self.scrivenerProjectBookmark = nil
        self.scrivenerItemID = nil
        self.scrivenerItemTitle = nil
        self.lastWordCharacters = nil
        self.lastWordModified = nil
        self.lastScrivenerCharacters = nil
        self.lastScrivenerModified = nil
        self.syncPaused = false
    }

    /// Записи этого этапа без повторов
    private var uniqueEntries: [Entry] {
        guard modelContext != nil else { return [] }
        var seen = Set<UUID>()
        return entries.filter { seen.insert($0.id).inserted }
    }

    var sortedEntries: [Entry] {
        guard modelContext != nil else { return [] }
        return uniqueEntries.sorted { $0.date < $1.date }
    }

    var currentProgress: Int {
        guard modelContext != nil else { return 0 }
        let total = sortedEntries.cumulativeProgress()
        return max(0, total)
    }

    var progressPercentage: Double {
        guard goal > 0 else { return 0 }
        let percent = Double(currentProgress) / Double(goal)
        return min(max(percent, 0), 1.0)
    }
}
#endif
