#if os(macOS)
import SwiftUI

struct DocumentSyncInfoView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject

    private var info: String {
        switch project.syncType {
        case .word:
            let path = DocumentSyncManager.resolvedPath(bookmark: project.wordFileBookmark,
                                                        path: project.wordFilePath)
            return settings.localized("sync_info_word", path ?? "")
        case .scrivener:
            let basePath = DocumentSyncManager.resolvedPath(bookmark: project.scrivenerProjectBookmark,
                                                            path: project.scrivenerProjectPath)
            var name = project.scrivenerItemID ?? ""
            if let basePath, let itemID = project.scrivenerItemID {
                let url = URL(fileURLWithPath: basePath)
                let items = ScrivenerParser.items(in: url)
                if let item = ScrivenerParser.findItem(withID: itemID, in: items) {
                    name = item.title
                }
            }
            return settings.localized("sync_info_scrivener", name, basePath ?? "")
        case .none:
            return ""
        }
    }

    var body: some View {
        VStack(spacing: scaledSpacing()) {
            Text(info)
                .frame(maxWidth: .infinity, alignment: .leading)
            Toggle(settings.localized("pause_sync"), isOn: $project.syncPaused)
                .toggleStyle(.switch)
                .onChange(of: project.syncPaused) { value in
                    if value { DocumentSyncManager.stopMonitoring(project: project) }
                    else { DocumentSyncManager.startMonitoring(project: project) }
                }
            if project.syncType == .scrivener {
                Button(settings.localized("change")) { changeItem() }
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

    private func changeItem() {
        guard let basePath = DocumentSyncManager.resolvedPath(bookmark: project.scrivenerProjectBookmark,
                                                               path: project.scrivenerProjectPath) else { return }
        let request = ScrivenerSelectRequest(projectID: project.id, projectPath: basePath)
        openWindow(id: "selectScrivenerItem", value: request)
        dismiss()
    }
}
#endif
