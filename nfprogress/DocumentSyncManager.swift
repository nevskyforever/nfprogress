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
    private static var stageWatchers: [UUID: DispatchSourceFileSystemObject] = [:]
    private static var stageTimers: [UUID: Timer] = [:]
    private static var stageAccessURLs: [UUID: URL] = [:]

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

    static func resolvedPath(bookmark: Data?, path: String?) -> String? {
        if let path, !path.isEmpty { return path }
        if let data = bookmark {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data,
                                   options: [.withSecurityScope],
                                   relativeTo: nil,
                                   bookmarkDataIsStale: &stale) {
                return url.path
            }
        }
        return nil
    }

    private static func fetchProject(id: PersistentIdentifier) -> WritingProject? {
        let descriptor = FetchDescriptor<WritingProject>(predicate: #Predicate { $0.id == id })
        return try? DataController.mainContext.fetch(descriptor).first
    }

    private static func fetchStage(id: UUID) -> Stage? {
        let descriptor = FetchDescriptor<Stage>(predicate: #Predicate { $0.id == id })
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
            project.wordFilePath = url.path
            url.startAccessingSecurityScopedResource()
            accessURLs[id] = url
            startWatcher(projectID: id, path: url.path) { checkWordFile(for: id) }
            checkWordFile(for: id)
        case .scrivener:
            guard let base = resolveURL(bookmark: &project.scrivenerProjectBookmark,
                                        path: project.scrivenerProjectPath) else { return }
            project.scrivenerProjectPath = base.path
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
        let timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { _ in handler() }
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
            if project.lastWordCharacters != nil {
                let entry = Entry(date: modDate, characterCount: count)
                entry.syncSource = .word
                project.entries.append(entry)
            }
            project.lastWordCharacters = count
            project.lastWordModified = modDate
            try? DataController.mainContext.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }

    // MARK: - Stage Monitoring

    static func startMonitoring(stage: Stage) {
        stopMonitoring(stage: stage)
        guard let type = stage.syncType else { return }
        let id = stage.id
        switch type {
        case .word:
            guard let url = resolveURL(bookmark: &stage.wordFileBookmark,
                                       path: stage.wordFilePath) else { return }
            stage.wordFilePath = url.path
            url.startAccessingSecurityScopedResource()
            stageAccessURLs[id] = url
            startWatcher(stageID: id, path: url.path) { checkWordFile(stageID: id) }
            checkWordFile(stageID: id)
        case .scrivener:
            guard let base = resolveURL(bookmark: &stage.scrivenerProjectBookmark,
                                        path: stage.scrivenerProjectPath) else { return }
            stage.scrivenerProjectPath = base.path
            base.startAccessingSecurityScopedResource()
            stageAccessURLs[id] = base
            guard let path = scrivenerFilePath(for: stage, baseURL: base) else {
                stopMonitoring(stage: stage)
                return
            }
            startWatcher(stageID: id, path: path) { checkScrivenerFile(stageID: id) }
            checkScrivenerFile(stageID: id)
        }
    }

    static func stopMonitoring(stage: Stage) {
        if let source = stageWatchers.removeValue(forKey: stage.id) { source.cancel() }
        if let timer = stageTimers.removeValue(forKey: stage.id) { timer.invalidate() }
        if let url = stageAccessURLs.removeValue(forKey: stage.id) {
            url.stopAccessingSecurityScopedResource()
        }
    }

    static func removeSync(stage: Stage) {
        stopMonitoring(stage: stage)
        guard let mainStage = fetchStage(id: stage.id) else { return }
        if let data = mainStage.wordFileBookmark {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data,
                                  options: [.withSecurityScope],
                                  relativeTo: nil,
                                  bookmarkDataIsStale: &stale) {
                url.stopAccessingSecurityScopedResource()
            }
        }
        if let data = mainStage.scrivenerProjectBookmark {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data,
                                  options: [.withSecurityScope],
                                  relativeTo: nil,
                                  bookmarkDataIsStale: &stale) {
                url.stopAccessingSecurityScopedResource()
            }
        }
        mainStage.syncType = nil
        mainStage.wordFilePath = nil
        mainStage.wordFileBookmark = nil
        mainStage.scrivenerProjectPath = nil
        mainStage.scrivenerProjectBookmark = nil
        mainStage.scrivenerItemID = nil
        mainStage.lastWordCharacters = nil
        mainStage.lastWordModified = nil
        mainStage.lastScrivenerCharacters = nil
        mainStage.lastScrivenerModified = nil
        try? DataController.mainContext.save()
    }

    private static func startWatcher(stageID: UUID, path: String, handler: @escaping () -> Void) {
        let fd = open(path, O_EVTONLY)
        guard fd >= 0 else { return }
        let mask: DispatchSource.FileSystemEvent = [.write, .delete, .rename]
        let source = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd,
                                                               eventMask: mask,
                                                               queue: .main)
        source.setEventHandler(handler: handler)
        source.setCancelHandler { close(fd) }
        stageWatchers[stageID] = source
        source.resume()
        let timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { _ in handler() }
        stageTimers[stageID] = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    static func checkWordFile(stageID id: UUID) {
        guard let stage = fetchStage(id: id),
              let url = resolveURL(bookmark: &stage.wordFileBookmark,
                                   path: stage.wordFilePath) else { return }
        let path = url.path
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let count = attrString.string.count
        if stage.lastWordCharacters != count || stage.lastWordModified != modDate {
            let previous: Int
            if let last = stage.lastWordCharacters {
                previous = last
            } else {
                previous = stage.startProgress + stage.currentProgress
            }
            let delta = count - previous
            let entry = Entry(date: modDate, characterCount: delta)
            entry.syncSource = .word
            stage.entries.append(entry)
            stage.lastWordCharacters = count
            stage.lastWordModified = modDate
            try? DataController.mainContext.save()
            NotificationCenter.default.post(name: .projectProgressChanged, object: nil)
        }
    }

    private static func scrivenerFilePath(for stage: Stage, baseURL: URL) -> String? {
        guard let itemID = stage.scrivenerItemID else { return nil }
        let dataURL = baseURL.appendingPathComponent("Files/Data/\(itemID)/content.rtf")
        if FileManager.default.fileExists(atPath: dataURL.path) {
            return dataURL.path
        }
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

    static func checkScrivenerFile(stageID id: UUID) {
        guard let stage = fetchStage(id: id),
              let base = resolveURL(bookmark: &stage.scrivenerProjectBookmark,
                                    path: stage.scrivenerProjectPath),
              let path = scrivenerFilePath(for: stage, baseURL: base) else { return }
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let count = attrString.string.count
        if stage.lastScrivenerCharacters != count || stage.lastScrivenerModified != modDate {
            let previous: Int
            if let last = stage.lastScrivenerCharacters {
                previous = last
            } else {
                previous = stage.startProgress + stage.currentProgress
            }
            let delta = count - previous
            let entry = Entry(date: modDate, characterCount: delta)
            entry.syncSource = .scrivener
            stage.entries.append(entry)
            stage.lastScrivenerCharacters = count
            stage.lastScrivenerModified = modDate
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
