#if os(macOS)
import SwiftUI
#if canImport(SwiftData)
import SwiftData
#endif
#if canImport(UserNotifications)
import UserNotifications
#endif
import UniformTypeIdentifiers

struct ImportExportView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @EnvironmentObject private var settings: AppSettings
    @Query(sort: [SortDescriptor(\WritingProject.order)]) private var projects: [WritingProject]

    @State private var selection = Set<PersistentIdentifier>()
    @State private var isImporting = false
    @State private var pendingImport: [WritingProject] = []
    @State private var showConflictAlert = false

    private var selectedProjects: [WritingProject] {
        projects.filter { selection.contains($0.id) }
    }

    var body: some View {
        VStack {
            List(selection: $selection) {
                ForEach(projects) { project in
                    Text(project.title)
                        .tag(project.id)
                }
            }
            .frame(minHeight: layoutStep(20))

            HStack {
                Button(settings.localized("import")) { isImporting = true }
                Spacer()
                Button(settings.localized("export")) { export() }
                    .buttonStyle(.borderedProminent)
                    .disabled(selection.isEmpty)
            }
        }
        .scaledPadding()
        .frame(minWidth: layoutStep(40), minHeight: layoutStep(30))
        .windowTitle(settings.localized("import_export"))
        .onExitCommand { dismiss() }
        .fileImporter(
            isPresented: $isImporting,
            allowedContentTypes: [.commaSeparatedText]
        ) { result in
            switch result {
            case .success(let url):
                importCSV(from: url)
            case .failure(let error):
                print("Import failed: \(error.localizedDescription)")
            }
        }
        .alert(settings.localized("import_conflict_question"), isPresented: $showConflictAlert) {
            Button(settings.localized("keep_all")) { keepAll() }
            Button(settings.localized("replace")) { replaceAll() }
        }
    }

    private func export() {
        let items = selectedProjects
        guard !items.isEmpty else { return }
        if items.count == 1, let project = items.first {
            exportSingle(project: project)
        } else {
            exportMultiple(projects: items)
        }
        dismiss()
    }

    private func exportSingle(project: WritingProject) {
        let csv = CSVManager.csvString(for: project)
        let name = project.title.replacingOccurrences(of: " ", with: "_") + ".csv"
        saveCSV(csv, defaultName: name)
    }

    private func exportMultiple(projects: [WritingProject]) {
        let csv = CSVManager.csvString(for: projects)
        saveCSV(csv, defaultName: "Projects.csv")
    }

    private func saveCSV(_ csv: String, defaultName: String) {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.commaSeparatedText]
        panel.nameFieldStringValue = defaultName
        if panel.runModal() == .OK, let url = panel.url {
            do {
                try csv.write(to: url, atomically: true, encoding: .utf8)
            } catch {
                print("Export failed: \(error.localizedDescription)")
            }
        }
    }

    private func importCSV(from url: URL) {
        guard let data = try? Data(contentsOf: url),
              let text = String(data: data, encoding: .utf8) else { return }
        let imported = CSVManager.importProjects(from: text)
        let existingTitles = Set(projects.map { $0.title })
        if imported.contains(where: { existingTitles.contains($0.title) }) {
            pendingImport = imported
            showConflictAlert = true
        } else {
            for project in imported {
                context.insert(project)
            }
            try? context.save()
        }
    }

    private func keepAll() {
        let existingTitles = Set(projects.map { $0.title })
        for project in pendingImport {
            if existingTitles.contains(project.title) {
                project.title += " — импорт"
            }
            context.insert(project)
        }
        try? context.save()
        pendingImport = []
        showConflictAlert = false
        dismiss()
    }

    private func replaceAll() {
        let existing = projects
        for imported in pendingImport {
            if let current = existing.first(where: { $0.title == imported.title }) {
                let stageSyncInfo = Dictionary(uniqueKeysWithValues: current.stages.map { ($0.title, $0) })
                let syncType = current.syncType
                let wordPath = current.wordFilePath
                let wordBookmark = current.wordFileBookmark
                let scrivenerPath = current.scrivenerProjectPath
                let scrivenerBookmark = current.scrivenerProjectBookmark
                let itemID = current.scrivenerItemID
                let itemName = current.scrivenerItemName
                let paused = current.syncPaused
                let lastWordChars = current.lastWordCharacters
                let lastScrivenerChars = current.lastScrivenerCharacters
                let lastWordMod = current.lastWordModified
                let lastScrivenerMod = current.lastScrivenerModified
                let lastShare = current.lastShareProgress

                current.goal = imported.goal
                current.deadline = imported.deadline
                current.entries = imported.entries
                current.stages = imported.stages
                current.lastShareProgress = imported.lastShareProgress

                for stage in current.stages {
                    if let old = stageSyncInfo[stage.title] {
                        stage.syncType = old.syncType
                        stage.wordFilePath = old.wordFilePath
                        stage.wordFileBookmark = old.wordFileBookmark
                        stage.scrivenerProjectPath = old.scrivenerProjectPath
                        stage.scrivenerProjectBookmark = old.scrivenerProjectBookmark
                        stage.scrivenerItemID = old.scrivenerItemID
                        stage.scrivenerItemName = old.scrivenerItemName
                        stage.syncPaused = old.syncPaused
                        stage.lastWordCharacters = old.lastWordCharacters
                        stage.lastWordModified = old.lastWordModified
                        stage.lastScrivenerCharacters = old.lastScrivenerCharacters
                        stage.lastScrivenerModified = old.lastScrivenerModified
                    }
                }

                current.syncType = syncType
                current.wordFilePath = wordPath
                current.wordFileBookmark = wordBookmark
                current.scrivenerProjectPath = scrivenerPath
                current.scrivenerProjectBookmark = scrivenerBookmark
                current.scrivenerItemID = itemID
                current.scrivenerItemName = itemName
                current.syncPaused = paused
                current.lastWordCharacters = lastWordChars
                current.lastScrivenerCharacters = lastScrivenerChars
                current.lastWordModified = lastWordMod
                current.lastScrivenerModified = lastScrivenerMod
                if current.lastShareProgress == nil {
                    current.lastShareProgress = lastShare
                }
            } else {
                context.insert(imported)
            }
        }
        try? context.save()
        pendingImport = []
        showConflictAlert = false
        dismiss()
        sendNotification()
    }

    private func sendNotification() {
        #if canImport(UserNotifications)
        let center = UNUserNotificationCenter.current()
        center.requestAuthorization(options: [.alert]) { granted, _ in
            guard granted else { return }
            let content = UNMutableNotificationContent()
            content.body = settings.localized("projects_imported_sync_saved")
            let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
            center.add(request)
        }
        #endif
    }
}
#endif
