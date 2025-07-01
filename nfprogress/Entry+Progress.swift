#if canImport(SwiftData)
import Foundation

extension Sequence where Element == Entry {
    /// Возвращает общий прогресс, корректно обрабатывая записи Scrivener,
    /// которые содержат абсолютное значение символов.
    func cumulativeProgress() -> Int {
        var result = 0
        for entry in self {
            if entry.syncSource == .scrivener {
                result = entry.characterCount
            } else {
                result += entry.characterCount
            }
        }
        return result
    }
}
#endif
