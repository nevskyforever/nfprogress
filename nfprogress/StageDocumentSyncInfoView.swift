#if os(macOS)
import SwiftUI

struct StageDocumentSyncInfoView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    @Bindable var stage: Stage

    private var info: String {
        switch stage.syncType {
        case .word:
            let path = DocumentSyncManager.resolvedPath(bookmark: stage.wordFileBookmark,
                                                        path: stage.wordFilePath)
            return String(format: settings.localized("sync_info_word"), path ?? "")
        case .scrivener:
            let basePath = DocumentSyncManager.resolvedPath(bookmark: stage.scrivenerProjectBookmark,
                                                            path: stage.scrivenerProjectPath)
            var name = stage.scrivenerItemID ?? ""
            if let basePath, let itemID = stage.scrivenerItemID {
                let url = URL(fileURLWithPath: basePath)
                let items = ScrivenerParser.items(in: url)
                if let item = items.first(where: { $0.id == itemID }) {
                    name = item.title
                }
            }
            return String(format: settings.localized("sync_info_scrivener"), name, basePath ?? "")
        case .none:
            return ""
        }
    }

    var body: some View {
        VStack(spacing: scaledSpacing()) {
            Text(info)
                .frame(maxWidth: .infinity, alignment: .leading)
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
}
#endif
