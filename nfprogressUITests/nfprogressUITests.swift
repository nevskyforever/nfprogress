//
//  nfprogressUITests.swift
//  nfprogressUITests
//
//  Created by Роман Кишочкин on 15.06.2025.
//

import XCTest

final class nfprogressUITests: XCTestCase {

    override func setUpWithError() throws {
        // Put setup code here. This method is called before the invocation of each test method in the class.

        // In UI tests it is usually best to stop immediately when a failure occurs.
        continueAfterFailure = false

        // In UI tests it’s important to set the initial state - such as interface orientation - required for your tests before they run. The setUp method is a good place to do this.
    }

    override func tearDownWithError() throws {
        // Put teardown code here. This method is called after the invocation of each test method in the class.
    }

    @MainActor
    func testExample() throws {
        // UI tests must launch the application that they test.
        let app = XCUIApplication()
        app.launch()

        // Use XCTAssert and related functions to verify your tests produce the correct results.
    }

    @MainActor
    func testScaledLayoutNoOverlap() throws {
        let app = XCUIApplication()
        app.launchEnvironment["OS_ACTIVITY_MODE"] = "disable"
        app.launchArguments += ["-textScale", "1.59"]
        app.launch()

        let detail = app.scrollViews.firstMatch
        XCTAssertFalse(detail.hasOverlappingRendering)
    }

    @MainActor
    func testSnapshot159() throws {
        let app = XCUIApplication()
        app.launchEnvironment["OS_ACTIVITY_MODE"] = "disable"
        app.launchArguments += ["-textScale", "1.59"]
        app.launch()

        let detail = app.scrollViews.firstMatch
        XCTAssertTrue(detail.waitForExistence(timeout: 5))
        let attachment = XCTAttachment(screenshot: detail.screenshot())
        attachment.name = "snapshot-159-\(UUID().uuidString)"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    @MainActor
    func testScaledLayoutExtremeSizes() throws {
        for scale in ["2.0", "2.5", "3.0"] {
            XCTContext.runActivity(named: "Scale \(scale)") { _ in
                let app = XCUIApplication()
                app.launchEnvironment["OS_ACTIVITY_MODE"] = "disable"
                app.launchArguments = ["-textScale", scale]
                app.launch()

                let detail = app.scrollViews.firstMatch
                XCTAssertFalse(detail.hasOverlappingRendering)

                #if os(iOS)
                if XCUIDevice.shared.supportsOrientationChanges {
                    XCUIDevice.shared.orientation = .landscapeLeft
                    XCTAssertFalse(detail.hasOverlappingRendering)
                    XCUIDevice.shared.orientation = .portrait
                }
                #endif

                app.terminate()
            }
        }
    }

    @MainActor
    func testLaunchPerformance() throws {
        // This measures how long it takes to launch your application.
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            XCUIApplication().launch()
        }
    }
}
