import XCTest
@testable import nfprogress

final class ColorInterpolationTests: XCTestCase {
    func testEdgeCases() {
        let start = Color.red
        let end = Color.blue
        XCTAssertEqual(Color.interpolate(from: start, to: end, fraction: 0), start)
        XCTAssertEqual(Color.interpolate(from: start, to: end, fraction: 1), end)
    }

    func testHueWrap() {
        let from = Color(hue: 0.95, saturation: 1, brightness: 1)
        let to = Color(hue: 0.05, saturation: 1, brightness: 1)
        let mid = Color.interpolate(from: from, to: to, fraction: 0.5)
#if canImport(AppKit) || canImport(UIKit)
        let h = mid.hsbComponents.h
        XCTAssert(h < 0.1 || h > 0.9)
#else
        let h = mid.hsbComponents.h
        XCTAssert(h < 0.1 || h > 0.9)
#endif
    }
}
