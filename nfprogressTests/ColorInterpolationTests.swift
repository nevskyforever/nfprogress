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
        #if canImport(AppKit)
        var h: CGFloat = 0, s: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        NSColor(mid).usingColorSpace(.deviceRGB)?.getHue(&h, saturation: &s, brightness: &b, alpha: &a)
        #elseif canImport(UIKit)
        var h: CGFloat = 0, s: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        UIColor(mid).getHue(&h, saturation: &s, brightness: &b, alpha: &a)
        #endif
        XCTAssert( (h < 0.1 || h > 0.9) )
    }
}
