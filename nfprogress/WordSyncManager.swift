#if os(macOS)
import Foundation
import AppKit
#if canImport(SwiftData)
import SwiftData
#endif

@MainActor
enum WordSyncManager {
    private static var watchers: [PersistentIdentifier: DispatchSourceFileSystemObject] = [:]

    static func startMonitoring(project: WritingProject) {
        stopMonitoring(project: project)
        guard let path = project.wordFilePath else { return }
        let fd = open(path, O_EVTONLY)
        guard fd >= 0 else { return }
        let source = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd,
                                                               eventMask: .write,
                                                               queue: .main)
        source.setEventHandler {
            checkFile(for: project)
        }
        source.setCancelHandler {
            close(fd)
        }
        watchers[project.id] = source
        source.resume()
        checkFile(for: project)
    }

    static func stopMonitoring(project: WritingProject) {
        if let source = watchers.removeValue(forKey: project.id) {
            source.cancel()
        }
    }

    static func checkFile(for project: WritingProject) {
        guard let path = project.wordFilePath else { return }
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let count = attrString.string.count
        if project.lastWordCharacters != count || project.lastWordModified != modDate {
            let delta = count - project.currentProgress
            let entry = Entry(date: modDate, characterCount: delta)
            entry.isWordEntry = true
            project.entries.append(entry)
            project.lastWordCharacters = count
            project.lastWordModified = modDate
            let context = ModelContext(DataController.shared)
            try? context.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }
}
#endif
