import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if canImport(SwiftUI)
import SwiftUI
#endif

extension Array where Element == Date {
    /// Calculates the minimal calendar component step so that labels don't overlap
    /// for the given chart width and text scale.
    func stride(forWidth width: CGFloat,
                fontScale: Double,
                minLabelSpacing: CGFloat = 80) -> Calendar.Component {
        guard !isEmpty else { return .day }
        let calendar = Calendar.current
        let allowed = Double(width / (minLabelSpacing * CGFloat(fontScale)))

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
    /// Sorted list of entry dates without duplicates.
    var sortedEntryDates: [Date] {
        let calendar = Calendar.current
        let dates = sortedEntries.map { calendar.startOfDay(for: $0.date) }
        return Array(Set(dates)).sorted()
    }
}
#endif
