import XCTest
@testable import nfprogress

final class FontScalingTests: XCTestCase {
    func testCalcFontSize() {
        let size = calcFontSize(token: .progressValue)
        XCTAssertEqual(size, 20)
        let large = calcFontSize(token: .progressValueLarge)
        XCTAssertEqual(large, 30)
    }
}
