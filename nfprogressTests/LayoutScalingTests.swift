import XCTest
@testable import nfprogress

final class LayoutScalingTests: XCTestCase {
    func testCalcLayoutValue() {
        for scale in TextScale.values {
            XCTAssertEqual(calcLayoutValue(base: 8, scaleFactor: scale), 8 * scale)
        }
    }
}
