#if os(macOS)
import SwiftUI
import AppKit

struct DocumentSyncInfoView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject

    @State private var infoText = ""
    @State private var syncURL: URL?

    var body: some View {
        VStack(spacing: scaledSpacing()) {
            Text(infoText)
                .frame(maxWidth: .infinity, alignment: .leading)
            if let url = syncURL {
                Button(settings.localized("show_in_finder")) { showInFinder(url) }
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
        .onAppear { updateInfo() }
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

    private func updateInfo() {
        switch project.syncType {
        case .word:
            syncURL = DocumentSyncManager.syncFileURL(for: project)
            let name = syncURL?.lastPathComponent ?? ""
            infoText = settings.localized("sync_info_word", name)
        case .scrivener:
            var name = project.scrivenerItemName ?? project.scrivenerItemID ?? ""
            var url: URL?
            if name.isEmpty || project.scrivenerItemName == nil,
               let base = DocumentSyncManager.resolveURL(bookmark: &project.scrivenerProjectBookmark,
                                                        path: project.scrivenerProjectPath),
               let itemID = project.scrivenerItemID {
                base.startAccessingSecurityScopedResource()
                let items = ScrivenerParser.items(in: base)
                base.stopAccessingSecurityScopedResource()
                if let item = ScrivenerParser.findItem(withID: itemID, in: items) {
                    name = item.title
                    project.scrivenerItemName = name
                    try? project.modelContext?.save()
                }
                if let path = DocumentSyncManager.scrivenerFilePath(for: project, baseURL: base) {
                    url = URL(fileURLWithPath: path)
                }
            } else if let basePath = DocumentSyncManager.resolvedPath(bookmark: project.scrivenerProjectBookmark,
                                                                     path: project.scrivenerProjectPath),
                      let path = DocumentSyncManager.scrivenerFilePath(for: project, baseURL: URL(fileURLWithPath: basePath)) {
                url = URL(fileURLWithPath: path)
            }
            syncURL = url
            infoText = settings.localized("sync_info_scrivener", name)
        case .none:
            infoText = ""
            syncURL = nil
        }
    }

    private func showInFinder(_ url: URL) {
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }
}
#endif
