import XCTest
#if canImport(SwiftData)
@testable import nfprogress

final class CSVImportTests: XCTestCase {
    func testLegacyImport() throws {
        let csv = "Title,Goal,Deadline,Date,Count\nProject A,500,2025-12-31,2025-01-01,100"
        let projects = CSVManager.importProjects(from: csv)
        XCTAssertEqual(projects.count, 1)
        XCTAssertEqual(projects[0].title, "Project A")
        XCTAssertEqual(projects[0].goal, 500)
        XCTAssertEqual(projects[0].entries.count, 1)
    }
}
#endif
