import XCTest
@testable import nfprogress

final class FontScalingTests: XCTestCase {
    func testCalcFontSize() {
        let size = calcFontSize(token: .progressValue, scaleFactor: 1.5)
        XCTAssertEqual(size, 30)
    }
}
