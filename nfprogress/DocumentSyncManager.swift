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

    private static func resolveURL(bookmark: inout Data?, path: String?) -> URL? {
        if let data = bookmark {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data,
                                   options: [.withSecurityScope],
                                   bookmarkDataIsStale: &stale) {
                if stale, let newData = try? url.bookmarkData(options: .withSecurityScope) {
                    bookmark = newData
                    try? DataController.mainContext.save()
                }
                url.startAccessingSecurityScopedResource()
                return url
            }
        }
        if let path, !path.isEmpty {
            let url = URL(fileURLWithPath: path)
            if let data = try? url.bookmarkData(options: .withSecurityScope) {
                bookmark = data
                try? DataController.mainContext.save()
            }
            url.startAccessingSecurityScopedResource()
            return url
        }
        return nil
    }

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
            guard let url = resolveURL(bookmark: &project.wordFileBookmark,
                                       path: project.wordFilePath) else { return }
            startWatcher(projectID: id, path: url.path) { checkWordFile(for: id) }
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

    static func removeSync(project: WritingProject) {
        stopMonitoring(project: project)
        if let data = project.wordFileBookmark,
           let url = try? URL(resolvingBookmarkData: data, options: [.withSecurityScope]) {
            url.stopAccessingSecurityScopedResource()
        }
        if let data = project.scrivenerProjectBookmark,
           let url = try? URL(resolvingBookmarkData: data, options: [.withSecurityScope]) {
            url.stopAccessingSecurityScopedResource()
        }
        project.syncType = nil
        project.wordFilePath = nil
        project.wordFileBookmark = nil
        project.scrivenerProjectPath = nil
        project.scrivenerProjectBookmark = nil
        project.scrivenerItemID = nil
        project.lastWordCharacters = nil
        project.lastWordModified = nil
        project.lastScrivenerCharacters = nil
        project.lastScrivenerModified = nil
        try? DataController.mainContext.save()
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
              let url = resolveURL(bookmark: &project.wordFileBookmark,
                                   path: project.wordFilePath) else { return }
        let path = url.path
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
        guard let itemID = project.scrivenerItemID,
              let baseURL = resolveURL(bookmark: &project.scrivenerProjectBookmark,
                                       path: project.scrivenerProjectPath) else { return nil }
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
