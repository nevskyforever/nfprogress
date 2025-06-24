#if os(macOS)
import Foundation
import AppKit
#if canImport(SwiftData)
import SwiftData
#endif

@MainActor
enum DocumentSyncManager {
    private static var watchers: [PersistentIdentifier: DispatchSourceFileSystemObject] = [:]
    private static var timers: [PersistentIdentifier: Timer] = [:]

    static func startMonitoring(project: WritingProject) {
        stopMonitoring(project: project)
        guard let type = project.syncType else { return }
        switch type {
        case .word:
            guard let path = project.wordFilePath else { return }
            startWatcher(project: project, path: path) { checkWordFile(for: project) }
            checkWordFile(for: project)
        case .scrivener:
            guard let projectPath = project.scrivenerProjectPath,
                  let itemID = project.scrivenerItemID else { return }
            let filePath = projectPath + "/Files/Docs/" + itemID + ".rtf"
            startWatcher(project: project, path: filePath) { checkScrivenerFile(for: project) }
            checkScrivenerFile(for: project)
        }
    }

    static func stopMonitoring(project: WritingProject) {
        if let source = watchers.removeValue(forKey: project.id) { source.cancel() }
        if let timer = timers.removeValue(forKey: project.id) { timer.invalidate() }
    }

    private static func startWatcher(project: WritingProject, path: String, handler: @escaping () -> Void) {
        let fd = open(path, O_EVTONLY)
        guard fd >= 0 else { return }
        let mask: DispatchSource.FileSystemEvent = [.write, .delete, .rename]
        let source = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd,
                                                               eventMask: mask,
                                                               queue: .main)
        source.setEventHandler(handler: handler)
        source.setCancelHandler { close(fd) }
        watchers[project.id] = source
        source.resume()
        let timer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { _ in handler() }
        timers[project.id] = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    static func checkWordFile(for project: WritingProject) {
        guard let path = project.wordFilePath else { return }
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let count = attrString.string.count
        if project.lastWordCharacters != count || project.lastWordModified != modDate {
            let delta = count - project.currentProgress
            let entry = Entry(date: modDate, characterCount: delta)
            entry.syncSource = .word
            project.entries.append(entry)
            project.lastWordCharacters = count
            project.lastWordModified = modDate
            let context = ModelContext(DataController.shared)
            try? context.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }

    static func checkScrivenerFile(for project: WritingProject) {
        guard let base = project.scrivenerProjectPath,
              let itemID = project.scrivenerItemID else { return }
        let path = base + "/Files/Docs/" + itemID + ".rtf"
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let count = attrString.string.count
        if project.lastScrivenerCharacters != count || project.lastScrivenerModified != modDate {
            let delta = count - project.currentProgress
            let entry = Entry(date: modDate, characterCount: delta)
            entry.syncSource = .scrivener
            project.entries.append(entry)
            project.lastScrivenerCharacters = count
            project.lastScrivenerModified = modDate
            let context = ModelContext(DataController.shared)
            try? context.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }
}
#endif
