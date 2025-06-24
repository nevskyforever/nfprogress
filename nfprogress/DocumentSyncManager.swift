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

    private static func fetchProject(id: PersistentIdentifier) -> WritingProject? {
        let descriptor = FetchDescriptor<WritingProject>(predicate: #Predicate { $0.id == id })
        return try? DataController.mainContext.fetch(descriptor).first
    }

    static func startMonitoring(project: WritingProject) {
        stopMonitoring(project: project)
        guard let type = project.syncType else { return }
        let id = project.id
        switch type {
        case .word:
            guard let path = project.wordFilePath else { return }
            startWatcher(projectID: id, path: path) { checkWordFile(for: id) }
            checkWordFile(for: id)
        case .scrivener:
            guard let path = scrivenerFilePath(for: project) else { return }
            startWatcher(projectID: id, path: path) { checkScrivenerFile(for: id) }
            checkScrivenerFile(for: id)
        }
    }

    static func stopMonitoring(project: WritingProject) {
        if let source = watchers.removeValue(forKey: project.id) { source.cancel() }
        if let timer = timers.removeValue(forKey: project.id) { timer.invalidate() }
    }

    private static func startWatcher(projectID: PersistentIdentifier, path: String, handler: @escaping () -> Void) {
        let fd = open(path, O_EVTONLY)
        guard fd >= 0 else { return }
        let mask: DispatchSource.FileSystemEvent = [.write, .delete, .rename]
        let source = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd,
                                                               eventMask: mask,
                                                               queue: .main)
        source.setEventHandler(handler: handler)
        source.setCancelHandler { close(fd) }
        watchers[projectID] = source
        source.resume()
        let timer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { _ in handler() }
        timers[projectID] = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    static func checkWordFile(for id: PersistentIdentifier) {
        guard let project = fetchProject(id: id),
              let path = project.wordFilePath else { return }
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let count = attrString.string.count
        if project.lastWordCharacters != count || project.lastWordModified != modDate {
            let entry = Entry(date: modDate, characterCount: count)
            entry.syncSource = .word
            project.entries.append(entry)
            project.lastWordCharacters = count
            project.lastWordModified = modDate
            try? DataController.mainContext.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }

    private static func scrivenerFilePath(for project: WritingProject) -> String? {
        guard let base = project.scrivenerProjectPath,
              let itemID = project.scrivenerItemID else { return nil }
        let baseURL = URL(fileURLWithPath: base)
        // Modern Scrivener projects store documents in Files/Data/<UUID>/content.rtf
        let dataURL = baseURL.appendingPathComponent("Files/Data/\(itemID)/content.rtf")
        if FileManager.default.fileExists(atPath: dataURL.path) {
            return dataURL.path
        }

        // Older projects keep files in Files/Docs directory with various extensions
        let docsURL = baseURL.appendingPathComponent("Files/Docs")
        let candidates = ["\(itemID).rtf", "\(itemID).txt", "\(itemID).rtfd/\(itemID).rtf"]
        for name in candidates {
            let p = docsURL.appendingPathComponent(name).path
            if FileManager.default.fileExists(atPath: p) { return p }
        }

        if let files = try? FileManager.default.contentsOfDirectory(atPath: docsURL.path) {
            if let match = files.first(where: { $0.hasPrefix(itemID + ".") }) {
                return docsURL.appendingPathComponent(match).path
            }
        }

        return nil
    }

    static func checkScrivenerFile(for id: PersistentIdentifier) {
        guard let project = fetchProject(id: id),
              let path = scrivenerFilePath(for: project) else { return }
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let count = attrString.string.count
        if project.lastScrivenerCharacters != count || project.lastScrivenerModified != modDate {
            let entry = Entry(date: modDate, characterCount: count)
            entry.syncSource = .scrivener
            project.entries.append(entry)
            project.lastScrivenerCharacters = count
            project.lastScrivenerModified = modDate
            try? DataController.mainContext.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }
}
#endif
