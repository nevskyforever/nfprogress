#if os(macOS)
import SwiftUI
import AppKit

struct StageDocumentSyncInfoView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var settings: AppSettings
    @Bindable var stage: Stage

    private var info: String {
        switch stage.syncType {
        case .word:
            let path = DocumentSyncManager.resolvedPath(bookmark: stage.wordFileBookmark,
                                                        path: stage.wordFilePath)
            return settings.localized("sync_info_word", path ?? "")
        case .scrivener:
            let basePath = DocumentSyncManager.resolvedPath(bookmark: stage.scrivenerProjectBookmark,
                                                            path: stage.scrivenerProjectPath)
            var name = stage.scrivenerItemID ?? ""
            if let basePath, let itemID = stage.scrivenerItemID {
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
            Toggle(settings.localized("pause_sync"), isOn: $stage.syncPaused)
                .toggleStyle(.switch)
                .onChange(of: stage.syncPaused) { value in
                    if value { DocumentSyncManager.stopMonitoring(stage: stage) }
                    else { DocumentSyncManager.startMonitoring(stage: stage) }
                }
            if stage.syncType == .scrivener {
                Button(settings.localized("change")) { changeScrivenerItem() }
            } else if stage.syncType == .word {
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
        DocumentSyncManager.removeSync(stage: stage)
        dismiss()
    }

    private func changeScrivenerItem() {
        guard let basePath = DocumentSyncManager.resolvedPath(bookmark: stage.scrivenerProjectBookmark,
                                                               path: stage.scrivenerProjectPath) else { return }
        let request = StageScrivenerSelectRequest(stageID: stage.id, projectPath: basePath)
        openWindow(id: "stageSelectScrivenerItem", value: request)
        dismiss()
    }

    private func changeWordFile() {
        let panel = NSOpenPanel()
        panel.allowedFileTypes = ["doc", "docx"]
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            if DocumentSyncManager.isWordFileInUse(url.path, excludingStage: stage.id) {
                let alert = NSAlert()
                alert.messageText = settings.localized("sync_already_linked")
                alert.runModal()
                return
            }
            stage.syncType = .word
            stage.wordFilePath = url.path
            stage.wordFileBookmark = try? url.bookmarkData(options: .withSecurityScope)
            try? stage.modelContext?.save()
            DocumentSyncManager.startMonitoring(stage: stage)
            dismiss()
        }
    }
}
#endif
