#if os(macOS)
import SwiftUI

struct DocumentSyncInfoView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var settings: AppSettings
    @Bindable var project: WritingProject

    private var info: String {
        switch project.syncType {
        case .word:
            var path = project.wordFilePath
            if path == nil, let data = project.wordFileBookmark {
                var stale = false
                if let url = try? URL(resolvingBookmarkData: data,
                                       options: [.withSecurityScope],
                                       relativeTo: nil,
                                       bookmarkDataIsStale: &stale) {
                    path = url.path
                }
            }
            return String(format: settings.localized("sync_info_word"), path ?? "")
        case .scrivener:
            var name = project.scrivenerItemID ?? ""
            var basePath = project.scrivenerProjectPath
            if basePath == nil, let data = project.scrivenerProjectBookmark {
                var stale = false
                if let url = try? URL(resolvingBookmarkData: data,
                                       options: [.withSecurityScope],
                                       relativeTo: nil,
                                       bookmarkDataIsStale: &stale) {
                    basePath = url.path
                }
            }
            if let basePath {
                let url = URL(fileURLWithPath: basePath)
                let items = ScrivenerParser.items(in: url)
                if let item = items.first(where: { $0.id == project.scrivenerItemID }) {
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
        DocumentSyncManager.removeSync(project: project)
        dismiss()
    }
}
#endif
