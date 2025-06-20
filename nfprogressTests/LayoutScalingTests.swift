import XCTest
@testable import nfprogress

final class LayoutScalingTests: XCTestCase {
    func testCalcLayoutValue() {
        XCTAssertEqual(calcLayoutValue(base: CGFloat(8)), CGFloat(8))
    }

    func testLayoutStep() {
        let expected = baseLayoutStep * 2
        XCTAssertEqual(layoutStep(2), expected)
    }
}
