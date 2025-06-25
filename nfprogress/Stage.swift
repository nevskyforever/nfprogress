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
    /// Последнее известное количество символов в Word
    var lastWordCharacters: Int?
    /// Последняя дата изменения Word
    var lastWordModified: Date?
    /// Последнее известное количество символов в Scrivener
    var lastScrivenerCharacters: Int?
    /// Последняя дата изменения Scrivener
    var lastScrivenerModified: Date?

    init(title: String, goal: Int, deadline: Date? = nil, startProgress: Int) {
        self.title = title
        self.goal = goal
        self.deadline = deadline
        self.startProgress = startProgress
        self.entries = []
        self.syncType = nil
        self.wordFilePath = nil
        self.wordFileBookmark = nil
        self.scrivenerProjectPath = nil
        self.scrivenerProjectBookmark = nil
        self.scrivenerItemID = nil
        self.lastWordCharacters = nil
        self.lastWordModified = nil
        self.lastScrivenerCharacters = nil
        self.lastScrivenerModified = nil
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
        var progress = 0
        let entries = sortedEntries
        for entry in entries {
            if entry.syncSource != nil {
                // Записи из синхронизации содержат абсолютное
                // количество символов на момент изменения файла
                progress = entry.characterCount
            } else {
                progress += entry.characterCount
            }
        }
        return max(0, progress)
    }

    var progressPercentage: Double {
        guard goal > 0 else { return 0 }
        let percent = Double(currentProgress) / Double(goal)
        return min(max(percent, 0), 1.0)
    }
}
#endif
