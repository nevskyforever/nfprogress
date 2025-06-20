import XCTest
#if canImport(CoreGraphics)
import CoreGraphics
#endif
@testable import nfprogress

final class ChartStrideTests: XCTestCase {
    func testMonthOfDailyData() {
        let calendar = Calendar.current
        let start = calendar.startOfDay(for: Date())
        let dates = (0..<30).compactMap { calendar.date(byAdding: .day, value: $0, to: start) }
        let comp = dates.stride(forWidth: CGFloat(640))
        XCTAssertEqual(comp, .weekOfYear)
    }

    func testFiveYearsData() {
        let calendar = Calendar.current
        let start = calendar.startOfDay(for: Date())
        let dates = (0..<1825).compactMap { calendar.date(byAdding: .day, value: $0, to: start) }
        let comp = dates.stride(forWidth: CGFloat(600))
        XCTAssertEqual(comp, .year)
    }
}
