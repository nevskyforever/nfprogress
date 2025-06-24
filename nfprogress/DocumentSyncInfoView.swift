#if os(macOS)
import SwiftUI

struct DocumentSyncInfoView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject

    private var info: String {
        switch project.syncType {
        case .word:
            let path = project.wordFilePath ?? ""
            return String(format: settings.localized("sync_info_word"), path)
        case .scrivener:
            var name = project.scrivenerItemID ?? ""
            if let base = project.scrivenerProjectPath {
                let url = URL(fileURLWithPath: base)
                let items = ScrivenerParser.items(in: url)
                if let item = items.first(where: { $0.id == project.scrivenerItemID }) {
                    name = item.title
                }
            }
            let path = project.scrivenerProjectPath ?? ""
            return String(format: settings.localized("sync_info_scrivener"), name, path)
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
        DocumentSyncManager.removeSync(project: project)
        dismiss()
    }
}
#endif
