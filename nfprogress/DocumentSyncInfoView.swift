#if os(macOS)
import SwiftUI
import AppKit

struct DocumentSyncInfoView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject

    private var wordPath: String? {
        DocumentSyncManager.resolvedPath(bookmark: project.wordFileBookmark,
                                         path: project.wordFilePath)
    }

    private var wordName: String? {
        if let path = wordPath { return URL(fileURLWithPath: path).lastPathComponent }
        return nil
    }

    private var scrivenerPath: String? {
        DocumentSyncManager.resolvedPath(bookmark: project.scrivenerProjectBookmark,
                                         path: project.scrivenerProjectPath)
    }

    private var scrivenerName: String {
        if let title = project.scrivenerItemTitle { return title }
        if let base = scrivenerPath, let itemID = project.scrivenerItemID {
            let url = URL(fileURLWithPath: base)
            url.startAccessingSecurityScopedResource()
            defer { url.stopAccessingSecurityScopedResource() }
            let items = ScrivenerParser.items(in: url)
            if let item = ScrivenerParser.findItem(withID: itemID, in: items) {
                project.scrivenerItemTitle = item.title
                try? project.modelContext?.save()
                return item.title
            }
        }
        return project.scrivenerItemID ?? ""
    }

    var body: some View {
        VStack(spacing: scaledSpacing()) {
            if project.syncType == .word {
                Text(String(format: settings.localized("sync_word_label"), wordName ?? ""))
                    .frame(maxWidth: .infinity, alignment: .leading)
                if let path = wordPath {
                    Button(settings.localized("show_in_finder")) { showInFinder(path) }
                }
            } else if project.syncType == .scrivener {
                Text(String(format: settings.localized("sync_scrivener_label"), scrivenerName))
                    .frame(maxWidth: .infinity, alignment: .leading)
                if let path = scrivenerPath {
                    Button(settings.localized("show_in_finder")) { showInFinder(path) }
                }
            }
            Toggle(settings.localized("pause_sync"), isOn: $project.syncPaused)
                .toggleStyle(.switch)
                .onChange(of: project.syncPaused) { value in
                    if value { DocumentSyncManager.stopMonitoring(project: project) }
                    else { DocumentSyncManager.startMonitoring(project: project) }
                }
            if project.syncType == .scrivener {
                Button(settings.localized("change")) { changeScrivenerItem() }
            } else if project.syncType == .word {
                Button(settings.localized("change")) { changeWordFile() }
            }
            Spacer()
            HStack {
                Spacer()
                Button(settings.localized("close")) { dismiss() }
                Button(settings.localized("unlink")) { unlink() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .scaledPadding()
        .frame(minWidth: layoutStep(40), minHeight: layoutStep(20))
        .windowTitle(settings.localized("sync_document_tooltip"))
    }

    private func unlink() {
        DocumentSyncManager.removeSync(project: project)
        dismiss()
    }

    private func changeScrivenerItem() {
        guard let basePath = DocumentSyncManager.resolvedPath(bookmark: project.scrivenerProjectBookmark,
                                                               path: project.scrivenerProjectPath) else { return }
        let request = ScrivenerSelectRequest(projectID: project.id, projectPath: basePath)
        openWindow(id: "selectScrivenerItem", value: request)
        dismiss()
    }

    private func changeWordFile() {
        let panel = NSOpenPanel()
        panel.allowedFileTypes = ["doc", "docx"]
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            if DocumentSyncManager.isWordFileInUse(url.path, excludingProject: project.id) {
                let alert = NSAlert()
                alert.messageText = settings.localized("sync_already_linked")
                alert.runModal()
                return
            }
            project.syncType = .word
            project.wordFilePath = url.path
            project.wordFileBookmark = try? url.bookmarkData(options: .withSecurityScope)
            try? project.modelContext?.save()
            DocumentSyncManager.startMonitoring(project: project)
            dismiss()
        }
    }

    private func showInFinder(_ path: String) {
        let url = URL(fileURLWithPath: path)
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }
}
#endif
