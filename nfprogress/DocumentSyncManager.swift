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
    private static var syncInterval: TimeInterval = {
        let v = UserDefaults.standard.double(forKey: "syncInterval")
        return v == 0 ? 2 : v
    }()
    private static var globallyPaused: Bool = UserDefaults.standard.bool(forKey: "pauseAllSync")

    static func updateSyncInterval(to value: TimeInterval) {
        syncInterval = value
        refreshAllTimers()
    }

    static func setGlobalPause(_ paused: Bool) {
        globallyPaused = paused
        if paused {
            stopAllMonitoring()
        } else {
            startAllMonitoring()
        }
    }

    private static func stopAllMonitoring() {
        let context = DataController.mainContext
        let desc = FetchDescriptor<WritingProject>()
        if let projects = try? context.fetch(desc) {
            for project in projects where project.syncType != nil {
                stopMonitoring(project: project)
            }
            for stage in projects.flatMap({ $0.stages }) where stage.syncType != nil {
                stopMonitoring(stage: stage)
            }
        }
    }

    private static func startAllMonitoring() {
        let context = DataController.mainContext
        let desc = FetchDescriptor<WritingProject>()
        if let projects = try? context.fetch(desc) {
            for project in projects where project.syncType != nil && !project.syncPaused {
                startMonitoring(project: project)
            }
            for stage in projects.flatMap({ $0.stages }) where stage.syncType != nil && !stage.syncPaused {
                startMonitoring(stage: stage)
            }
        }
    }

    private static func refreshAllTimers() {
        for (id, timer) in timers {
            timer.invalidate()
            guard let project = fetchProject(id: id) else { continue }
            let handler: () -> Void = {
                switch project.syncType {
                case .word: checkWordFile(for: id)
                case .scrivener: checkScrivenerFile(for: id)
                case .none: break
                }
            }
            let t = Timer.scheduledTimer(withTimeInterval: syncInterval, repeats: true) { _ in handler() }
            timers[id] = t
            RunLoop.main.add(t, forMode: .common)
        }
        for (id, timer) in stageTimers {
            timer.invalidate()
            guard let stage = fetchStage(id: id) else { continue }
            let handler: () -> Void = {
                switch stage.syncType {
                case .word: checkWordFile(stageID: id)
                case .scrivener: checkScrivenerFile(stageID: id)
                case .none: break
                }
            }
            let t = Timer.scheduledTimer(withTimeInterval: syncInterval, repeats: true) { _ in handler() }
            stageTimers[id] = t
            RunLoop.main.add(t, forMode: .common)
        }
    }

    /// Возвращает идентификатор проекта, которому принадлежит этап
    private static func projectID(for stage: Stage) -> PersistentIdentifier? {
        let desc = FetchDescriptor<WritingProject>()
        if let projects = try? DataController.mainContext.fetch(desc) {
            return projects.first(where: { $0.stages.contains(where: { $0.id == stage.id }) })?.id
        }
        return nil
    }

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

    static func isWordFileInUse(_ path: String, excludingProject: PersistentIdentifier? = nil, excludingStage: UUID? = nil) -> Bool {
        let desc = FetchDescriptor<WritingProject>()
        if let projects = try? DataController.mainContext.fetch(desc) {
            for project in projects {
                if project.id != excludingProject && project.wordFilePath == path && project.syncType == .word {
                    return true
                }
                for stage in project.stages where stage.id != excludingStage {
                    if stage.wordFilePath == path && stage.syncType == .word {
                        return true
                    }
                }
            }
        }
        return false
    }

    static func isScrivenerItemInUse(projectPath: String, itemID: String, excludingProject: PersistentIdentifier? = nil, excludingStage: UUID? = nil) -> Bool {
        let desc = FetchDescriptor<WritingProject>()
        if let projects = try? DataController.mainContext.fetch(desc) {
            for project in projects {
                if project.id != excludingProject && project.scrivenerProjectPath == projectPath && project.scrivenerItemID == itemID && project.syncType == .scrivener {
                    return true
                }
                for stage in project.stages where stage.id != excludingStage {
                    if stage.scrivenerProjectPath == projectPath && stage.scrivenerItemID == itemID && stage.syncType == .scrivener {
                        return true
                    }
                }
            }
        }
        return false
    }

    private static func fetchProject(id: PersistentIdentifier) -> WritingProject? {
        let descriptor = FetchDescriptor<WritingProject>(predicate: #Predicate { $0.id == id })
        return try? DataController.mainContext.fetch(descriptor).first
    }

    private static func fetchStage(id: UUID) -> Stage? {
        let descriptor = FetchDescriptor<Stage>(predicate: #Predicate { $0.id == id })
        return try? DataController.mainContext.fetch(descriptor).first
    }

    /// Выполняет синхронизацию проекта один раз независимо от состояния паузы.
    /// Периодическая синхронизация не возобновляется автоматически.
    static func syncNow(project: WritingProject) {
        guard let type = project.syncType else { return }
        let id = project.id
        switch type {
        case .word:
            if let url = resolveURL(bookmark: &project.wordFileBookmark,
                                   path: project.wordFilePath) {
                url.startAccessingSecurityScopedResource()
                defer { url.stopAccessingSecurityScopedResource() }
                checkWordFile(for: id)
            }
        case .scrivener:
            if let base = resolveURL(bookmark: &project.scrivenerProjectBookmark,
                                     path: project.scrivenerProjectPath) {
                base.startAccessingSecurityScopedResource()
                defer { base.stopAccessingSecurityScopedResource() }
                checkScrivenerFile(for: id)
            }
        }
    }

    /// Выполняет синхронизацию этапа один раз независимо от состояния паузы.
    /// Периодическая синхронизация не возобновляется автоматически.
    static func syncNow(stage: Stage) {
        guard let type = stage.syncType else { return }
        let id = stage.id
        switch type {
        case .word:
            if let url = resolveURL(bookmark: &stage.wordFileBookmark,
                                   path: stage.wordFilePath) {
                url.startAccessingSecurityScopedResource()
                defer { url.stopAccessingSecurityScopedResource() }
                checkWordFile(stageID: id)
            }
        case .scrivener:
            if let base = resolveURL(bookmark: &stage.scrivenerProjectBookmark,
                                     path: stage.scrivenerProjectPath) {
                base.startAccessingSecurityScopedResource()
                defer { base.stopAccessingSecurityScopedResource() }
                checkScrivenerFile(stageID: id)
            }
        }
    }

    static func startMonitoring(project: WritingProject) {
        stopMonitoring(project: project)
        guard !globallyPaused, !project.syncPaused, let type = project.syncType else { return }
        let id = project.id
        switch type {
        case .word:
            guard let url = resolveURL(bookmark: &project.wordFileBookmark,
                                       path: project.wordFilePath) else { return }
            if isWordFileInUse(url.path, excludingProject: id) { return }
            project.wordFilePath = url.path
            url.startAccessingSecurityScopedResource()
            accessURLs[id] = url
            startWatcher(projectID: id, path: url.path) { checkWordFile(for: id) }
            checkWordFile(for: id)
        case .scrivener:
            guard let base = resolveURL(bookmark: &project.scrivenerProjectBookmark,
                                        path: project.scrivenerProjectPath) else { return }
            if let itemID = project.scrivenerItemID,
               isScrivenerItemInUse(projectPath: base.path, itemID: itemID, excludingProject: id) {
                return
            }
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
        let timer = Timer.scheduledTimer(withTimeInterval: syncInterval, repeats: true) { _ in handler() }
        timers[projectID] = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    /// Вычисляет изменение прогресса исходя из абсолютного значения в файле,
    /// предыдущего сохранённого значения и текущего прогресса проекта или этапа.
    private static func computeDelta(totalCount: Int, last: Int?, current: Int) -> Int {
        if let last {
            return totalCount - last
        } else {
            return totalCount - current
        }
    }

    /// Создаёт запись синхронизации для проекта
    private static func recordSync(
        project: WritingProject,
        totalCount: Int,
        modDate: Date,
        lastCountKey: ReferenceWritableKeyPath<WritingProject, Int?>,
        lastModKey: ReferenceWritableKeyPath<WritingProject, Date?>,
        source: SyncDocumentType
    ) {
        let delta = computeDelta(totalCount: totalCount,
                                last: project[keyPath: lastCountKey],
                                current: project.currentProgress)
        let entry = Entry(date: modDate, characterCount: delta)
        entry.syncSource = source
        project.entries.append(entry)
        project[keyPath: lastCountKey] = totalCount
        project[keyPath: lastModKey] = modDate
        try? DataController.mainContext.save()
        NotificationCenter.default.post(name: .projectProgressChanged, object: project.id)
    }

    /// Создаёт запись синхронизации для этапа
    private static func recordSync(
        stage: Stage,
        totalCount: Int,
        modDate: Date,
        lastCountKey: ReferenceWritableKeyPath<Stage, Int?>,
        lastModKey: ReferenceWritableKeyPath<Stage, Date?>,
        source: SyncDocumentType
    ) {
        let current = stage.startProgress + stage.currentProgress
        let delta = computeDelta(totalCount: totalCount,
                                last: stage[keyPath: lastCountKey],
                                current: current)
        let entry = Entry(date: modDate, characterCount: delta)
        entry.syncSource = source
        stage.entries.append(entry)
        stage[keyPath: lastCountKey] = totalCount
        stage[keyPath: lastModKey] = modDate
        try? DataController.mainContext.save()
        let pid = projectID(for: stage)
        NotificationCenter.default.post(name: .projectProgressChanged, object: pid)
    }

    static func checkWordFile(for id: PersistentIdentifier) {
        guard let project = fetchProject(id: id),
              let url = resolveURL(bookmark: &project.wordFileBookmark,
                                   path: project.wordFilePath) else { return }
        let path = url.path
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let totalCount = attrString.string.count // абсолютное количество символов в файле
        if project.lastWordCharacters != totalCount || project.lastWordModified != modDate {
            recordSync(project: project,
                       totalCount: totalCount,
                       modDate: modDate,
                       lastCountKey: \WritingProject.lastWordCharacters,
                       lastModKey: \WritingProject.lastWordModified,
                       source: .word)
        }
    }

    // MARK: - Stage Monitoring

    static func startMonitoring(stage: Stage) {
        stopMonitoring(stage: stage)
        guard !globallyPaused, !stage.syncPaused, let type = stage.syncType else { return }
        let id = stage.id
        switch type {
        case .word:
            guard let url = resolveURL(bookmark: &stage.wordFileBookmark,
                                       path: stage.wordFilePath) else { return }
            if isWordFileInUse(url.path, excludingStage: id) { return }
            stage.wordFilePath = url.path
            url.startAccessingSecurityScopedResource()
            stageAccessURLs[id] = url
            startWatcher(stageID: id, path: url.path) { checkWordFile(stageID: id) }
            checkWordFile(stageID: id)
        case .scrivener:
            guard let base = resolveURL(bookmark: &stage.scrivenerProjectBookmark,
                                        path: stage.scrivenerProjectPath) else { return }
            if let itemID = stage.scrivenerItemID,
               isScrivenerItemInUse(projectPath: base.path, itemID: itemID, excludingStage: id) {
                return
            }
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
        let timer = Timer.scheduledTimer(withTimeInterval: syncInterval, repeats: true) { _ in handler() }
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
        let totalCount = attrString.string.count // абсолютное количество символов в файле
        if stage.lastWordCharacters != totalCount || stage.lastWordModified != modDate {
            recordSync(stage: stage,
                       totalCount: totalCount,
                       modDate: modDate,
                       lastCountKey: \Stage.lastWordCharacters,
                       lastModKey: \Stage.lastWordModified,
                       source: .word)
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
        base.startAccessingSecurityScopedResource()
        defer { base.stopAccessingSecurityScopedResource() }
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let totalCount = attrString.string.count // абсолютное количество символов в файле
        if stage.lastScrivenerCharacters != totalCount || stage.lastScrivenerModified != modDate {
            recordSync(stage: stage,
                       totalCount: totalCount,
                       modDate: modDate,
                       lastCountKey: \Stage.lastScrivenerCharacters,
                       lastModKey: \Stage.lastScrivenerModified,
                       source: .scrivener)
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
        base.startAccessingSecurityScopedResource()
        defer { base.stopAccessingSecurityScopedResource() }
        let url = URL(fileURLWithPath: path)
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: path),
              let modDate = attrs[.modificationDate] as? Date else { return }
        guard let attrString = try? NSAttributedString(url: url, options: [:], documentAttributes: nil) else { return }
        let totalCount = attrString.string.count // абсолютное количество символов в файле
        if project.lastScrivenerCharacters != totalCount || project.lastScrivenerModified != modDate {
            recordSync(project: project,
                       totalCount: totalCount,
                       modDate: modDate,
                       lastCountKey: \WritingProject.lastScrivenerCharacters,
                       lastModKey: \WritingProject.lastScrivenerModified,
                       source: .scrivener)
        }
    }
}
#endif
