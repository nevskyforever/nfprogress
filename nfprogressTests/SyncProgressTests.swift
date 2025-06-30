#if canImport(SwiftData)
import XCTest
@testable import nfprogress

final class SyncProgressTests: XCTestCase {
    func testProgressBetweenSyncEntries() {
        let project = WritingProject(title: "Test", goal: 1000)
        let date1 = Date()
        let entry1 = Entry(date: date1, characterCount: 100)
        entry1.syncSource = .word
        project.entries.append(entry1)

        let date2 = date1.addingTimeInterval(60)
        let entry2 = Entry(date: date2, characterCount: 20)
        entry2.syncSource = .word
        project.entries.append(entry2)

        let total1 = project.globalProgress(for: entry1)
        let total2 = project.globalProgress(for: entry2)
        XCTAssertEqual(total1, 100)
        XCTAssertEqual(total2, 120)
        XCTAssertEqual(total2 - total1, 20)
    }

    func testProjectProgressWithStageSyncEntries() {
        let project = WritingProject(title: "Test", goal: 1000)
        let stage = Stage(title: "Stage", goal: 500, deadline: nil, startProgress: 0)
        project.stages.append(stage)
        let date1 = Date()
        let entry1 = Entry(date: date1, characterCount: 50)
        entry1.syncSource = .scrivener
        stage.entries.append(entry1)

        let date2 = date1.addingTimeInterval(30)
        let entry2 = Entry(date: date2, characterCount: 25)
        entry2.syncSource = .scrivener
        stage.entries.append(entry2)

        let entries = project.sortedEntries
        guard let i1 = entries.firstIndex(where: { $0.id == entry1.id }),
              let i2 = entries.firstIndex(where: { $0.id == entry2.id }) else {
            XCTFail("Entries not found")
            return
        }
        let total1 = entries.prefix(i1 + 1).reduce(0) { $0 + $1.characterCount }
        let total2 = entries.prefix(i2 + 1).reduce(0) { $0 + $1.characterCount }
        XCTAssertEqual(total1, 50)
        XCTAssertEqual(total2, 75)
        XCTAssertEqual(total2 - total1, 25)
    }
}
#endif
