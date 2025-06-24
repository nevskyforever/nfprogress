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
    private static var accessURLs: [PersistentIdentifier: URL] = [:]

    private static func resolveURL(bookmark: inout Data?, path: String?) -> URL? {
        if let data = bookmark {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data,
                                   options: [.withSecurityScope],
                                   relativeTo: nil,
                                   bookmarkDataIsStale: &stale) {
                if stale, let newData = try? url.bookmarkData(options: .withSecurityScope) {
                    bookmark = newData
                    try? DataController.mainContext.save()
                }
                return url
            }
        }
        if let path, !path.isEmpty {
            let url = URL(fileURLWithPath: path)
            if let data = try? url.bookmarkData(options: .withSecurityScope) {
                bookmark = data
                try? DataController.mainContext.save()
            }
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
            url.startAccessingSecurityScopedResource()
            accessURLs[id] = url
            startWatcher(projectID: id, path: url.path) { checkWordFile(for: id) }
            checkWordFile(for: id)
        case .scrivener:
            guard let base = resolveURL(bookmark: &project.scrivenerProjectBookmark,
                                        path: project.scrivenerProjectPath) else { return }
            base.startAccessingSecurityScopedResource()
            accessURLs[id] = base
            guard let path = scrivenerFilePath(for: project, baseURL: base) else {
                stopMonitoring(project: project)
                return
            }
            startWatcher(projectID: id, path: path) { checkScrivenerFile(for: id) }
            checkScrivenerFile(for: id)
        }
    }

    static func stopMonitoring(project: WritingProject) {
        if let source = watchers.removeValue(forKey: project.id) { source.cancel() }
        if let timer = timers.removeValue(forKey: project.id) { timer.invalidate() }
        if let url = accessURLs.removeValue(forKey: project.id) {
            url.stopAccessingSecurityScopedResource()
        }
    }

    static func removeSync(project: WritingProject) {
        stopMonitoring(project: project)
        let id = project.id
        guard let mainProject = fetchProject(id: id) else { return }
        if let data = mainProject.wordFileBookmark {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data,
                                  options: [.withSecurityScope],
                                  relativeTo: nil,
                                  bookmarkDataIsStale: &stale) {
                url.stopAccessingSecurityScopedResource()
            }
        }
        if let data = mainProject.scrivenerProjectBookmark {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data,
                                  options: [.withSecurityScope],
                                  relativeTo: nil,
                                  bookmarkDataIsStale: &stale) {
                url.stopAccessingSecurityScopedResource()
            }
        }
        mainProject.syncType = nil
        mainProject.wordFilePath = nil
        mainProject.wordFileBookmark = nil
        mainProject.scrivenerProjectPath = nil
        mainProject.scrivenerProjectBookmark = nil
        mainProject.scrivenerItemID = nil
        mainProject.lastWordCharacters = nil
        mainProject.lastWordModified = nil
        mainProject.lastScrivenerCharacters = nil
        mainProject.lastScrivenerModified = nil
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

    private static func scrivenerFilePath(for project: WritingProject, baseURL: URL) -> String? {
        guard let itemID = project.scrivenerItemID else { return nil }
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
              let base = resolveURL(bookmark: &project.scrivenerProjectBookmark,
                                    path: project.scrivenerProjectPath),
              let path = scrivenerFilePath(for: project, baseURL: base) else { return }
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
