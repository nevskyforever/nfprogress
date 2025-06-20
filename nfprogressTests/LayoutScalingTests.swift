import XCTest
@testable import nfprogress

final class LayoutScalingTests: XCTestCase {
    func testCalcLayoutValue() {
        for scale in TextScale.values {
            let expected = CGFloat(8) * CGFloat(scale)
            XCTAssertEqual(calcLayoutValue(base: CGFloat(8), scaleFactor: scale), expected)
        }
    }

    func testLayoutStep() {
        for scale in TextScale.values {
            let expected = baseLayoutStep * 2 * CGFloat(scale)
            XCTAssertEqual(layoutStep(2, scaleFactor: scale), expected)
        }
    }
}
