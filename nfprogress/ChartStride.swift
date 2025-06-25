import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if canImport(SwiftUI)
import SwiftUI
#endif

extension Array where Element == Date {
    /// Вычисляет минимальный шаг календаря, чтобы подписи не перекрывались
    /// при заданной ширине графика.
    func stride(forWidth width: CGFloat,
                minLabelSpacing: CGFloat = 80) -> Calendar.Component {
        guard !isEmpty else { return .day }
        let calendar = Calendar.current
        let allowed = Double(width / minLabelSpacing)

        func count(for component: Calendar.Component) -> Int {
            var set = Set<Date>()
            for date in self {
                if let start = calendar.dateInterval(of: component, for: date)?.start {
                    set.insert(start)
                }
            }
            return set.count
        }

        for component in [Calendar.Component.day,
                          .weekOfYear,
                          .month,
                          .year] {
            if Double(count(for: component)) <= allowed {
                return component
            }
        }
        return .year
    }
}

#if canImport(SwiftData)
import SwiftData

extension WritingProject {
    /// Отсортированный список дат записей без повторений.
    var sortedEntryDates: [Date] {
        let calendar = Calendar.current
        let dates = sortedEntries.map { calendar.startOfDay(for: $0.date) }
        return Array(Set(dates)).sorted()
    }

    /// Подписи для оси графика в порядке записей.
    /// Каждой записи соответствует текст, содержащий дату и время
    /// (при нескольких записях в день показывается только время).
    var entryAxisLabels: [String] {
        let calendar = Calendar.current
        var lastDay: Date?
        var result: [String] = []
        for entry in sortedEntries {
            let day = calendar.startOfDay(for: entry.date)
            let label: String
            if day != lastDay {
                label = entry.date.formatted(date: .numeric, time: .shortened)
            } else {
                label = entry.date.formatted(date: .omitted, time: .shortened)
            }
            result.append(label)
            lastDay = day
        }
        return result
    }
}
#endif
