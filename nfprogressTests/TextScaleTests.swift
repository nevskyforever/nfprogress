import XCTest
@preconcurrency import Foundation
@testable import nfprogress

final class TextScaleTests: XCTestCase {
    func testQuantization() {
        XCTAssertEqual(TextScale.quantized(0.5), 1.0)
        XCTAssertEqual(TextScale.quantized(1.12), 1.0)
        XCTAssertEqual(TextScale.quantized(1.13), 1.25)
        XCTAssertEqual(TextScale.quantized(1.62), 1.5)
        XCTAssertEqual(TextScale.quantized(2.2), 2.0)
    }

    func testUserDefaultsPersistence() async {
        let suite = "TextScaleTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)

        let settings = await MainActor.run { AppSettings(userDefaults: defaults) }
        let value1 = await MainActor.run { settings.textScale }
        XCTAssertEqual(value1, 1.0)

        await MainActor.run { settings.textScale = 1.75 }
        XCTAssertEqual(defaults.double(forKey: "textScale"), 1.75)

        let newSettings = await MainActor.run { AppSettings(userDefaults: defaults) }
        let value2 = await MainActor.run { newSettings.textScale }
        XCTAssertEqual(value2, 1.75)
    }
}

